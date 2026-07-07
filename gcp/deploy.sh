#!/usr/bin/env bash
# Deploys calendar-agent to Cloud Run: 4 private sub-agent services plus one
# public-but-IAP-gated orchestrator service, state persisted on a GCS
# bucket mounted into the containers.
#
# Prerequisites (one-time, done by you before running this):
#   1. gcloud CLI installed and authenticated: `gcloud auth login`
#   2. A GCP project with billing enabled.
#   3. An OAuth consent screen configured for the project (Console ->
#      APIs & Services -> OAuth consent screen -> External -> add yourself
#      as a test user). IAP needs this to exist; it isn't scriptable
#      reliably across all account types, so it's not automated here.
#   4. Local one-time setup already done (see main README steps 1-6):
#      orchestrator/.env filled in, calendar OAuth authorized
#      (credentials/token.json exists), Handshake logged in
#      (sub_agents/job_agent/browser_profiles/handshake/ exists).
#
# Usage:
#   export PROJECT_ID=my-gcp-project
#   export REGION=us-central1                 # optional, this is the default
#   export BUCKET_NAME=my-calendar-agent-state
#   export IAP_USER_EMAIL=you@gmail.com        # who's allowed through IAP
#   ./gcp/deploy.sh
#
# Re-running is safe: resource-creation steps are skipped if the resource
# already exists, and `gcloud run deploy` on an existing service just
# creates a new revision.

set -euo pipefail
cd "$(dirname "$0")/.."

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${BUCKET_NAME:?Set BUCKET_NAME}"
: "${IAP_USER_EMAIL:?Set IAP_USER_EMAIL to the Google account that should be allowed through}"
REGION="${REGION:-us-central1}"
REPO="$REGION-docker.pkg.dev/$PROJECT_ID/calendar-agent"
ORCH_SA="calendar-agent-orchestrator@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "$PROJECT_ID" >/dev/null

echo "=== 1. Enabling required APIs ==="
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iap.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com

echo "=== 2. Artifact Registry repo ==="
gcloud artifacts repositories describe calendar-agent --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create calendar-agent \
    --repository-format=docker --location="$REGION" \
    --description="calendar-agent images"
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

echo "=== 3. GCS bucket for persistent state ==="
gsutil ls -b "gs://$BUCKET_NAME" >/dev/null 2>&1 || gsutil mb -l "$REGION" "gs://$BUCKET_NAME"

echo "=== 4. Seeding bucket with existing local state (if present) ==="
[ -d credentials ] && gsutil -m rsync -r credentials "gs://$BUCKET_NAME/credentials" || true
[ -d sub_agents/job_agent/data ] && gsutil -m rsync -r sub_agents/job_agent/data "gs://$BUCKET_NAME/job_agent/data" || true
[ -d sub_agents/job_agent/browser_profiles ] && gsutil -m rsync -r sub_agents/job_agent/browser_profiles "gs://$BUCKET_NAME/job_agent/browser_profiles" || true
[ -d sub_agents/shopping_agent/data ] && gsutil -m rsync -r sub_agents/shopping_agent/data "gs://$BUCKET_NAME/shopping_agent/data" || true
[ -d sub_agents/remedy_agent/data ] && gsutil -m rsync -r sub_agents/remedy_agent/data "gs://$BUCKET_NAME/remedy_agent/data" || true

echo "=== 5. GOOGLE_API_KEY in Secret Manager ==="
if ! gcloud secrets describe google-api-key >/dev/null 2>&1; then
  API_KEY="$(grep -E '^GOOGLE_API_KEY=' orchestrator/.env | cut -d= -f2-)"
  [ -n "$API_KEY" ] || { echo "GOOGLE_API_KEY is empty in orchestrator/.env"; exit 1; }
  printf '%s' "$API_KEY" | gcloud secrets create google-api-key --data-file=-
fi

echo "=== 6. Dedicated service account for the orchestrator ==="
gcloud iam service-accounts describe "$ORCH_SA" >/dev/null 2>&1 || \
  gcloud iam service-accounts create calendar-agent-orchestrator \
    --display-name="calendar-agent orchestrator"

echo "=== 7. Building and pushing images ==="
docker build -t "$REPO/agent-base:latest" -f Dockerfile .
docker build -t "$REPO/job-agent:latest" -f Dockerfile.job_agent .
docker push "$REPO/agent-base:latest"
docker push "$REPO/job-agent:latest"

echo "=== 8. Deploying sub-agents (private — invoker-only) ==="

gcloud run deploy example-specialist \
  --image="$REPO/agent-base:latest" \
  --region="$REGION" --no-allow-unauthenticated --port=8080 \
  --command="uvicorn" \
  --args="sub_agents.example_specialist.server:a2a_app,--host,0.0.0.0,--port,8080" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest"
EXAMPLE_SPECIALIST_URL="$(gcloud run services describe example-specialist --region="$REGION" --format='value(status.url)')"

gcloud run deploy job-agent \
  --image="$REPO/job-agent:latest" \
  --region="$REGION" --no-allow-unauthenticated --port=8080 \
  --command="uvicorn" \
  --args="sub_agents.job_agent.server:a2a_app,--host,0.0.0.0,--port,8080" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars="JOB_AGENT_DB_PATH=/mnt/state/job_agent/data/job_agent.db,BROWSER_PROFILES_DIR=/mnt/state/job_agent/browser_profiles,SQLITE_JOURNAL_MODE=DELETE,PLAYWRIGHT_HEADLESS=true" \
  --add-volume="mount-path=/mnt/state,type=cloud-storage,bucket=$BUCKET_NAME" \
  --memory=2Gi
JOB_AGENT_URL="$(gcloud run services describe job-agent --region="$REGION" --format='value(status.url)')"

gcloud run deploy shopping-agent \
  --image="$REPO/agent-base:latest" \
  --region="$REGION" --no-allow-unauthenticated --port=8080 \
  --command="uvicorn" \
  --args="sub_agents.shopping_agent.server:a2a_app,--host,0.0.0.0,--port,8080" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars="SHOPPING_AGENT_DB_PATH=/mnt/state/shopping_agent/data/shopping_agent.db,SQLITE_JOURNAL_MODE=DELETE" \
  --add-volume="mount-path=/mnt/state,type=cloud-storage,bucket=$BUCKET_NAME"
SHOPPING_AGENT_URL="$(gcloud run services describe shopping-agent --region="$REGION" --format='value(status.url)')"

gcloud run deploy remedy-agent \
  --image="$REPO/agent-base:latest" \
  --region="$REGION" --no-allow-unauthenticated --port=8080 \
  --command="uvicorn" \
  --args="sub_agents.remedy_agent.server:a2a_app,--host,0.0.0.0,--port,8080" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars="REMEDY_AGENT_DB_PATH=/mnt/state/remedy_agent/data/remedy_agent.db,SQLITE_JOURNAL_MODE=DELETE" \
  --add-volume="mount-path=/mnt/state,type=cloud-storage,bucket=$BUCKET_NAME"
REMEDY_AGENT_URL="$(gcloud run services describe remedy-agent --region="$REGION" --format='value(status.url)')"

echo "=== 9. Granting the orchestrator's service account invoker on each sub-agent ==="
for svc in example-specialist job-agent shopping-agent remedy-agent; do
  gcloud run services add-iam-policy-binding "$svc" \
    --region="$REGION" \
    --member="serviceAccount:$ORCH_SA" \
    --role=roles/run.invoker
done

echo "=== 10. Deploying the orchestrator (public URL, gated by IAP) ==="
gcloud run deploy orchestrator \
  --image="$REPO/agent-base:latest" \
  --region="$REGION" --no-allow-unauthenticated --iap --port=8080 \
  --service-account="$ORCH_SA" \
  --command="adk" \
  --args="web,--host,0.0.0.0,--port,8080" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=FALSE,USE_GCP_ID_TOKEN_AUTH=true,GOOGLE_CLIENT_SECRETS_FILE=/mnt/state/credentials/client_secret.json,GOOGLE_TOKEN_FILE=/mnt/state/credentials/token.json,GOOGLE_CALENDAR_ID=primary,GOOGLE_CALENDAR_TIMEZONE=UTC,EXAMPLE_SPECIALIST_AGENT_CARD_URL=${EXAMPLE_SPECIALIST_URL}/.well-known/agent-card.json,JOB_AGENT_CARD_URL=${JOB_AGENT_URL}/.well-known/agent-card.json,SHOPPING_AGENT_CARD_URL=${SHOPPING_AGENT_URL}/.well-known/agent-card.json,REMEDY_AGENT_CARD_URL=${REMEDY_AGENT_URL}/.well-known/agent-card.json" \
  --add-volume="mount-path=/mnt/state,type=cloud-storage,bucket=$BUCKET_NAME"

echo "=== 11. Granting IAP access to $IAP_USER_EMAIL ==="
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud run services add-iam-policy-binding orchestrator \
  --region="$REGION" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role=roles/run.invoker
gcloud iap web add-iam-policy-binding \
  --member="user:$IAP_USER_EMAIL" \
  --role=roles/iap.httpsResourceAccessor \
  --region="$REGION" --resource-type=cloud-run --service=orchestrator

ORCH_URL="$(gcloud run services describe orchestrator --region="$REGION" --format='value(status.url)')"
echo
echo "=== Done ==="
echo "Orchestrator (sign in with $IAP_USER_EMAIL): ${ORCH_URL}/dev-ui/"
echo "Sub-agents are private — not directly reachable except by the orchestrator."
