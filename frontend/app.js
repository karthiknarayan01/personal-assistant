const ORCH_BASE = "http://localhost:8000";
const APP_NAME = "orchestrator";
const USER_ID = "frontend-user";

let currentDeals = [];

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function escapeAttr(str) {
  return escapeHtml(str).replace(/"/g, "&quot;");
}

function showError(message) {
  const banner = document.getElementById("error-banner");
  banner.textContent = message;
  banner.hidden = false;
}

function clearError() {
  const banner = document.getElementById("error-banner");
  banner.hidden = true;
}

function appendChatBubble(role, text) {
  const log = document.getElementById("chat-log");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  log.appendChild(bubble);
  bubble.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function ensureSession() {
  let id = sessionStorage.getItem("adk_session_id");
  if (id) return id;

  const resp = await fetch(
    `${ORCH_BASE}/apps/${APP_NAME}/users/${USER_ID}/sessions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }
  );
  if (!resp.ok) throw new Error(`session create failed: ${resp.status}`);
  const session = await resp.json();
  sessionStorage.setItem("adk_session_id", session.id);
  return session.id;
}

async function runTurn(sessionId, userText, onEvent) {
  const resp = await fetch(`${ORCH_BASE}/run_sse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      app_name: APP_NAME,
      user_id: USER_ID,
      session_id: sessionId,
      new_message: { role: "user", parts: [{ text: userText }] },
      streaming: false,
    }),
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`run_sse failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let frameEnd;
    while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, frameEnd);
      buffer = buffer.slice(frameEnd + 2);
      const dataLines = frame.split("\n").filter((l) => l.startsWith("data:"));
      if (dataLines.length === 0) continue;
      const jsonText = dataLines.map((l) => l.slice(5).trimStart()).join("\n");
      let event;
      try {
        event = JSON.parse(jsonText);
      } catch {
        continue;
      }
      onEvent(event);
    }
  }
}

function setLoading(isLoading) {
  document.getElementById("loading-indicator").hidden = !isLoading;
  document.getElementById("send-btn").disabled = isLoading;
  document.getElementById("prompt-input").disabled = isLoading;
  if (!isLoading) {
    document.getElementById("prompt-input").focus();
  }
}

async function submitPrompt(text) {
  clearError();
  appendChatBubble("user", text);
  setLoading(true);

  const sessionId = await ensureSession();
  const deals = new Map();
  let assistantText = "";

  try {
    await runTurn(sessionId, text, (event) => {
      if (event.error) {
        assistantText += `\n[error: ${event.error}]`;
        return;
      }
      const parts = event.content?.parts || [];
      for (const part of parts) {
        if (part.functionResponse?.name === "search_slickdeals") {
          const r = part.functionResponse.response;
          if (r?.status === "success") {
            for (const d of r.deals || []) {
              deals.set(d.buy_url || d.url, d);
            }
          }
        }
        if (part.text && event.content?.role === "model") {
          assistantText += part.text;
        }
      }
    });
  } catch (e) {
    showError(
      `Could not reach the orchestrator at ${ORCH_BASE} — is it running? (${e.message})`
    );
    return;
  } finally {
    setLoading(false);
  }

  if (deals.size > 0) {
    showCardsView([...deals.values()]);
  } else {
    document.getElementById("cards-view").hidden = true;
    document.getElementById("details-view").hidden = true;
    appendChatBubble("assistant", assistantText || "(no response)");
  }
}

function showCardsView(deals) {
  currentDeals = deals;
  document.getElementById("cards-view").hidden = false;
  document.getElementById("details-view").hidden = true;

  const grid = document.getElementById("cards-grid");
  grid.innerHTML = "";
  deals.forEach((d, i) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      ${
        d.image_url
          ? `<img src="${escapeAttr(d.image_url)}" alt="">`
          : `<div class="no-image">No image</div>`
      }
      <h3>${escapeHtml(d.title)}</h3>
      ${d.price ? `<p class="price">${escapeHtml(d.price)}</p>` : ""}
      ${d.retailer ? `<p class="retailer">${escapeHtml(d.retailer)}</p>` : ""}
      ${
        d.discount_percent
          ? `<span class="badge">${d.discount_percent}% off</span>`
          : ""
      }
      ${d.free_shipping ? `<span class="badge">Free shipping</span>` : ""}
    `;
    card.addEventListener("click", () => showDetailsView(i));
    grid.appendChild(card);
  });
}

function showDetailsView(idx) {
  const d = currentDeals[idx];
  document.getElementById("cards-view").hidden = true;
  document.getElementById("details-view").hidden = false;

  const buyUrl = d.buy_url || d.url;
  const isFallback = !d.buy_url || d.buy_url === d.url;

  document.getElementById("details-content").innerHTML = `
    ${
      d.image_url
        ? `<img src="${escapeAttr(d.image_url)}" alt="" class="details-image">`
        : `<div class="no-image details-image">No image</div>`
    }
    <h2>${escapeHtml(d.title)}</h2>
    ${d.price ? `<p class="price">${escapeHtml(d.price)}</p>` : ""}
    ${d.retailer ? `<p class="retailer">${escapeHtml(d.retailer)}</p>` : ""}
    ${
      d.discount_percent
        ? `<span class="badge">${d.discount_percent}% off</span>`
        : ""
    }
    ${d.free_shipping ? `<span class="badge">Free shipping</span>` : ""}
    <p>${escapeHtml(d.description)}</p>
    <a href="${escapeAttr(buyUrl)}" target="_blank" rel="noopener noreferrer" class="buy-link">
      ${isFallback ? "View deal on Slickdeals" : "Buy at retailer"}
    </a>
  `;
}

document.getElementById("back-btn").addEventListener("click", () => {
  document.getElementById("details-view").hidden = true;
  document.getElementById("cards-view").hidden = false;
});

document.getElementById("prompt-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("prompt-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  submitPrompt(text);
});
