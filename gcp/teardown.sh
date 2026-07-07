#!/usr/bin/env bash
# Removes everything gcp/deploy.sh created. The GCS bucket (your actual
# data: purchase history, applied-jobs ledger, Handshake session, calendar
# token) is NOT deleted by default — pass --delete-bucket to also wipe it.

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
BUCKET_NAME="${BUCKET_NAME:-}"

gcloud config set project "$PROJECT_ID" >/dev/null

for svc in orchestrator example-specialist job-agent shopping-agent; do
  gcloud run services delete "$svc" --region="$REGION" --quiet || true
done

gcloud iam service-accounts delete \
  "calendar-agent-orchestrator@${PROJECT_ID}.iam.gserviceaccount.com" --quiet || true

gcloud secrets delete google-api-key --quiet || true

if [ "${1:-}" = "--delete-bucket" ]; then
  : "${BUCKET_NAME:?Set BUCKET_NAME to delete it}"
  gsutil -m rm -r "gs://$BUCKET_NAME" || true
else
  echo "Bucket ${BUCKET_NAME:-<unset>} left in place. Re-run with --delete-bucket (and BUCKET_NAME set) to remove it too."
fi
