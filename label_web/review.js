// label_web/review.js
// Admin review. Served from `python3 -m http.server`, so the origin is
// http://localhost:<port>, which app/main.py's _DEV_ORIGIN_REGEX already allows.
// Opening this file as file:// sends `Origin: null` and every fetch fails.

const params = new URLSearchParams(location.search);
const API = (params.get("api") || "http://localhost:8000").replace(/\/$/, "");
const TOKEN = params.get("token") || localStorage.getItem("silvertech_admin_token") || "";
if (params.get("token")) localStorage.setItem("silvertech_admin_token", params.get("token"));

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const els = {
  connection: document.getElementById("connection"),
  queue: document.getElementById("queue"),
  emptyState: document.getElementById("emptyState"),
  buttonList: document.getElementById("buttonList"),
  buttonName: document.getElementById("buttonName"),
  buttonUsage: document.getElementById("buttonUsage"),
  reviewerNote: document.getElementById("reviewerNote"),
  accept: document.getElementById("accept"),
  reject: document.getElementById("reject"),
  result: document.getElementById("result"),
};

const state = {
  submissionId: null,
  labels: null,
  image: null,
  scale: 1,
  selected: null,
  drawing: null,
  edited: false,
};

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    ...options,
    headers: { "X-Admin-Token": TOKEN, "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    // friendly_error() raises HTTPException(detail={message_vi, recovery_action}),
    // which FastAPI wraps as {"detail": {...}} — the Vietnamese message is
    // therefore under body.detail.message_vi, not body.message_vi.
    const body = await response.json().catch(() => ({}));
    const messageVi = typeof body.detail === "object" ? body.detail?.message_vi : body.detail;
    throw new Error(`${response.status}: ${messageVi || path}`);
  }
  return response.json();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!state.image) return;
  canvas.width = Math.round(state.image.width * state.scale);
  canvas.height = Math.round(state.image.height * state.scale);
  ctx.drawImage(state.image, 0, 0, canvas.width, canvas.height);

  drawBox(ctx, state.labels.template.logo_bbox, state.scale, "#c27803", "logo");
  state.labels.buttons.forEach((button, index) => {
    drawBox(
      ctx,
      button.bbox_template_coordinates,
      state.scale,
      "#256fb3",
      button.vietnamese_name || button.button_id,
      index === state.selected,
    );
  });
  if (state.drawing) drawBox(ctx, state.drawing, state.scale, "#cc3b3b", "moi");
}

function renderButtons() {
  els.buttonList.innerHTML = "";
  state.labels.buttons.forEach((button, index) => {
    const item = document.createElement("li");
    const pick = document.createElement("button");
    pick.textContent = `${button.button_id} — ${button.vietnamese_name || "(chưa đặt tên)"}`;
    pick.addEventListener("click", () => {
      state.selected = index;
      els.buttonName.value = button.vietnamese_name || "";
      els.buttonUsage.value = button.function_description || "";
      draw();
    });
    item.appendChild(pick);
    els.buttonList.appendChild(item);
  });
}

async function loadQueue() {
  els.queue.innerHTML = "";
  try {
    const rows = await api("/api/admin/submissions?status=pending");
    els.connection.textContent = `${API} — ${rows.length} mẫu đang chờ`;
    for (const row of rows) {
      const item = document.createElement("li");
      const pick = document.createElement("button");
      pick.textContent = `${row.brand} ${row.appliance_type}`;
      pick.addEventListener("click", () => loadSubmission(row.id));
      item.appendChild(pick);
      els.queue.appendChild(item);
    }
  } catch (error) {
    els.connection.textContent = String(error);
  }
}

async function loadSubmission(submissionId) {
  const detail = await api(`/api/admin/submissions/${submissionId}`);
  state.submissionId = submissionId;
  state.labels = detail.proposed_labels_json;
  state.selected = null;
  state.edited = false;
  els.result.textContent = "";

  const image = new Image();
  image.crossOrigin = "anonymous";
  image.onload = () => {
    state.image = image;
    state.scale = Math.min(1, 960 / image.width);
    els.emptyState.style.display = "none";
    renderButtons();
    draw();
  };
  image.src = `${API}/${detail.image_url}`;
}

canvas.addEventListener("pointerdown", (evt) => {
  if (state.selected === null || !state.image) return;
  const start = screenToImage(evt, canvas, state.scale);
  state.drawing = box(start.x, start.y, 0, 0);
  state.origin = start;
});

canvas.addEventListener("pointermove", (evt) => {
  if (!state.drawing) return;
  const now = screenToImage(evt, canvas, state.scale);
  state.drawing = box(state.origin.x, state.origin.y, now.x - state.origin.x, now.y - state.origin.y);
  draw();
});

canvas.addEventListener("pointerup", () => {
  if (!state.drawing) return;
  if (state.drawing.width > 4 && state.drawing.height > 4) {
    state.labels.buttons[state.selected].bbox_template_coordinates = state.drawing;
    state.edited = true;
  }
  state.drawing = null;
  draw();
});

for (const [input, field] of [
  [els.buttonName, "vietnamese_name"],
  [els.buttonUsage, "function_description"],
]) {
  input.addEventListener("input", () => {
    if (state.selected === null) return;
    state.labels.buttons[state.selected][field] = input.value;
    state.edited = true;
    renderButtons();
    draw();
  });
}

els.accept.addEventListener("click", async () => {
  if (!state.submissionId) return;
  const payload = state.edited
    ? { decision: "edit", edited_template: state.labels, reviewer_note: els.reviewerNote.value || null }
    : { decision: "accept", reviewer_note: els.reviewerNote.value || null };
  try {
    const result = await api(`/api/admin/submissions/${state.submissionId}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    els.result.textContent = `Đã duyệt. template_id: ${result.template_id}`;
    await loadQueue();
  } catch (error) {
    els.result.textContent = String(error);
  }
});

els.reject.addEventListener("click", async () => {
  if (!state.submissionId) return;
  try {
    await api(`/api/admin/submissions/${state.submissionId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision: "reject", reviewer_note: els.reviewerNote.value || null }),
    });
    els.result.textContent = "Đã từ chối.";
    await loadQueue();
  } catch (error) {
    els.result.textContent = String(error);
  }
});

loadQueue();
