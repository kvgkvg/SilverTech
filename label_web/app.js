const state = {
  image: null,
  imageName: "",
  imageWidth: 0,
  imageHeight: 0,
  scale: 1,
  panelBox: null,
  logoBox: null,
  buttons: [],
  selectedButtonId: null,
  drawing: null,
};

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const els = {
  emptyState: document.getElementById("emptyState"),
  imageInput: document.getElementById("imageInput"),
  drawMode: document.getElementById("drawMode"),
  fitImage: document.getElementById("fitImage"),
  deleteSelected: document.getElementById("deleteSelected"),
  saveDraft: document.getElementById("saveDraft"),
  loadDraft: document.getElementById("loadDraft"),
  clearDraft: document.getElementById("clearDraft"),
  newButton: document.getElementById("newButton"),
  buttonList: document.getElementById("buttonList"),
  buttonCount: document.getElementById("buttonCount"),
  panelReadout: document.getElementById("panelReadout"),
  logoReadout: document.getElementById("logoReadout"),
  buttonBoxReadout: document.getElementById("buttonBoxReadout"),
  exportOutput: document.getElementById("exportOutput"),
};

const fields = [
  "brand",
  "applianceType",
  "modelName",
  "displayName",
  "deviceId",
  "deviceStatus",
  "templateCode",
  "templateImageUrl",
  "descriptorPath",
  "templateId",
  "version",
  "templateStatus",
  "buttonId",
  "buttonType",
  "buttonLabel",
  "buttonVietnameseName",
  "buttonDescription",
].reduce((acc, id) => {
  acc[id] = document.getElementById(id);
  return acc;
}, {});

function slug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function nowIso() {
  return new Date().toISOString();
}

function box(x, y, width, height) {
  const nx = Math.round(Math.min(x, x + width));
  const ny = Math.round(Math.min(y, y + height));
  return {
    x: nx,
    y: ny,
    width: Math.round(Math.abs(width)),
    height: Math.round(Math.abs(height)),
  };
}

function screenToImage(evt) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (evt.clientX - rect.left) / state.scale,
    y: (evt.clientY - rect.top) / state.scale,
  };
}

function selectedButton() {
  return state.buttons.find((button) => button.localId === state.selectedButtonId) || null;
}

function selectedButtonIndex() {
  return state.buttons.findIndex((button) => button.localId === state.selectedButtonId);
}

function defaultButton() {
  return {
    localId: crypto.randomUUID(),
    button_id: "",
    label: "",
    vietnamese_name: "",
    function_description: "",
    button_type: "physical",
    bbox_template_coordinates: null,
    polygon_template_coordinates: null,
  };
}

function deriveIds() {
  const brand = slug(fields.brand.value);
  const appliance = slug(fields.applianceType.value);
  const model = slug(fields.modelName.value || fields.displayName.value || "template");
  if (!fields.deviceId.value && brand && appliance) {
    fields.deviceId.value = `device_${brand}_${appliance}_01`;
  }
  if (!fields.templateCode.value && brand && model) {
    fields.templateCode.value = `${brand}_${model}_v1`;
  }
  if (!fields.templateId.value && fields.templateCode.value) {
    fields.templateId.value = `template_${fields.templateCode.value}`;
  }
  if (!fields.templateImageUrl.value && state.imageName) {
    fields.templateImageUrl.value = `data/templates/${state.imageName}`;
  }
  if (!fields.descriptorPath.value && fields.templateCode.value) {
    fields.descriptorPath.value = `data/descriptors/${fields.templateCode.value}.npz`;
  }
}

function readForm() {
  deriveIds();
  const selected = selectedButton();
  if (selected) {
    selected.button_id = fields.buttonId.value.trim();
    selected.label = fields.buttonLabel.value.trim();
    selected.vietnamese_name = fields.buttonVietnameseName.value.trim();
    selected.function_description = fields.buttonDescription.value.trim();
    selected.button_type = fields.buttonType.value;
  }
}

function writeSelectedButtonForm() {
  const selected = selectedButton();
  const disabled = !selected;
  fields.buttonId.disabled = disabled;
  fields.buttonLabel.disabled = disabled;
  fields.buttonVietnameseName.disabled = disabled;
  fields.buttonDescription.disabled = disabled;
  fields.buttonType.disabled = disabled;
  if (!selected) {
    fields.buttonId.value = "";
    fields.buttonLabel.value = "";
    fields.buttonVietnameseName.value = "";
    fields.buttonDescription.value = "";
    fields.buttonType.value = "physical";
    els.buttonBoxReadout.textContent = "No selected button";
    return;
  }
  fields.buttonId.value = selected.button_id;
  fields.buttonLabel.value = selected.label;
  fields.buttonVietnameseName.value = selected.vietnamese_name;
  fields.buttonDescription.value = selected.function_description;
  fields.buttonType.value = selected.button_type;
  els.buttonBoxReadout.textContent = selected.bbox_template_coordinates
    ? JSON.stringify(selected.bbox_template_coordinates)
    : "Draw a button box on the image";
}

function drawBox(rect, color, label, active = false) {
  if (!rect) return;
  const x = rect.x * state.scale;
  const y = rect.y * state.scale;
  const w = rect.width * state.scale;
  const h = rect.height * state.scale;
  ctx.save();
  ctx.lineWidth = active ? 4 : 2;
  ctx.strokeStyle = color;
  ctx.fillStyle = `${color}22`;
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);
  ctx.fillStyle = color;
  ctx.font = "700 13px system-ui";
  const text = label || "";
  const textWidth = ctx.measureText(text).width + 10;
  ctx.fillRect(x, Math.max(0, y - 22), textWidth, 22);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(text, x + 5, Math.max(14, y - 7));
  ctx.restore();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (state.image) {
    canvas.width = Math.max(960, Math.round(state.imageWidth * state.scale));
    canvas.height = Math.max(640, Math.round(state.imageHeight * state.scale));
    ctx.drawImage(
      state.image,
      0,
      0,
      state.imageWidth * state.scale,
      state.imageHeight * state.scale,
    );
  }

  drawBox(state.panelBox, "#16834a", "panel");
  drawBox(state.logoBox, "#c27803", "logo");
  for (const button of state.buttons) {
    drawBox(
      button.bbox_template_coordinates,
      "#256fb3",
      button.button_id || button.label || "button",
      button.localId === state.selectedButtonId,
    );
  }

  if (state.drawing) {
    drawBox(state.drawing.rect, "#cc3b3b", state.drawing.mode);
  }
}

function refresh() {
  readForm();
  els.emptyState.style.display = state.image ? "none" : "grid";
  els.panelReadout.textContent = state.panelBox ? JSON.stringify(state.panelBox) : "not labeled";
  els.logoReadout.textContent = state.logoBox ? JSON.stringify(state.logoBox) : "not labeled";
  els.buttonCount.textContent = String(state.buttons.length);

  els.buttonList.innerHTML = "";
  for (const button of state.buttons) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `buttonItem ${button.localId === state.selectedButtonId ? "active" : ""}`;
    item.innerHTML = `
      <span class="buttonMeta">
        <strong>${button.button_id || "unnamed_button"}</strong>
        <span>${button.label || "No label"} · ${button.button_type}</span>
      </span>
      <span>${button.bbox_template_coordinates ? "boxed" : "no box"}</span>
    `;
    item.addEventListener("click", () => {
      readForm();
      state.selectedButtonId = button.localId;
      writeSelectedButtonForm();
      refresh();
    });
    els.buttonList.appendChild(item);
  }

  writeSelectedButtonForm();
  updateExport("json");
  draw();
}

function makePayload() {
  readForm();
  const templateId = fields.templateId.value.trim();
  const deviceId = fields.deviceId.value.trim();
  const stamp = nowIso();
  return {
    device: {
      id: deviceId,
      brand: fields.brand.value.trim(),
      appliance_type: fields.applianceType.value.trim(),
      model_name: fields.modelName.value.trim() || null,
      display_name: fields.displayName.value.trim(),
      status: fields.deviceStatus.value,
      created_at: stamp,
      updated_at: stamp,
    },
    template: {
      id: templateId,
      device_id: deviceId,
      template_code: fields.templateCode.value.trim(),
      template_image_url: fields.templateImageUrl.value.trim(),
      logo_bbox: state.logoBox,
      panel_bbox: state.panelBox,
      feature_descriptor_path: fields.descriptorPath.value.trim() || null,
      version: Number(fields.version.value || 1),
      status: fields.templateStatus.value,
      created_at: stamp,
      updated_at: stamp,
    },
    buttons: state.buttons.map((button) => ({
      id: `btn_${templateId.replace(/^template_/, "")}_${button.button_id || button.localId.slice(0, 8)}`,
      template_id: templateId,
      button_id: button.button_id,
      label: button.label,
      vietnamese_name: button.vietnamese_name,
      function_description: button.function_description,
      bbox_template_coordinates: button.bbox_template_coordinates,
      polygon_template_coordinates: button.polygon_template_coordinates,
      button_type: button.button_type,
      created_at: stamp,
      updated_at: stamp,
    })),
  };
}

function sqlString(value) {
  if (value === null || value === undefined || value === "") return "NULL";
  return `'${String(value).replaceAll("'", "''")}'`;
}

function sqlJson(value) {
  return value == null ? "NULL" : sqlString(JSON.stringify(value));
}

function makeSql(payload) {
  const d = payload.device;
  const t = payload.template;
  const lines = [
    "PRAGMA foreign_keys = ON;",
    `INSERT OR REPLACE INTO devices (id, brand, appliance_type, model_name, display_name, status, created_at, updated_at) VALUES (${sqlString(d.id)}, ${sqlString(d.brand)}, ${sqlString(d.appliance_type)}, ${sqlString(d.model_name)}, ${sqlString(d.display_name)}, ${sqlString(d.status)}, ${sqlString(d.created_at)}, ${sqlString(d.updated_at)});`,
    `INSERT OR REPLACE INTO templates (id, device_id, template_code, template_image_url, logo_bbox, panel_bbox, feature_descriptor_path, version, status, created_at, updated_at) VALUES (${sqlString(t.id)}, ${sqlString(t.device_id)}, ${sqlString(t.template_code)}, ${sqlString(t.template_image_url)}, ${sqlJson(t.logo_bbox)}, ${sqlJson(t.panel_bbox)}, ${sqlString(t.feature_descriptor_path)}, ${Number(t.version || 1)}, ${sqlString(t.status)}, ${sqlString(t.created_at)}, ${sqlString(t.updated_at)});`,
  ];
  for (const b of payload.buttons) {
    lines.push(
      `INSERT OR REPLACE INTO buttons (id, template_id, button_id, label, vietnamese_name, function_description, bbox_template_coordinates, polygon_template_coordinates, button_type, created_at, updated_at) VALUES (${sqlString(b.id)}, ${sqlString(b.template_id)}, ${sqlString(b.button_id)}, ${sqlString(b.label)}, ${sqlString(b.vietnamese_name)}, ${sqlString(b.function_description)}, ${sqlJson(b.bbox_template_coordinates)}, ${sqlJson(b.polygon_template_coordinates)}, ${sqlString(b.button_type)}, ${sqlString(b.created_at)}, ${sqlString(b.updated_at)});`,
    );
  }
  return lines.join("\n");
}

function updateExport(kind = "json") {
  const payload = makePayload();
  els.exportOutput.value =
    kind === "sql" ? makeSql(payload) : JSON.stringify(payload, null, 2);
}

function hitTestButton(point) {
  for (let i = state.buttons.length - 1; i >= 0; i--) {
    const button = state.buttons[i];
    const rect = button.bbox_template_coordinates;
    if (
      rect &&
      point.x >= rect.x &&
      point.x <= rect.x + rect.width &&
      point.y >= rect.y &&
      point.y <= rect.y + rect.height
    ) {
      return button;
    }
  }
  return null;
}

canvas.addEventListener("mousedown", (evt) => {
  if (!state.image) return;
  readForm();
  const point = screenToImage(evt);
  const mode = els.drawMode.value;
  if (mode === "button") {
    let button = selectedButton();
    if (!button) {
      button = defaultButton();
      state.buttons.push(button);
      state.selectedButtonId = button.localId;
    }
  }
  state.drawing = {
    mode,
    start: point,
    rect: box(point.x, point.y, 0, 0),
  };
});

canvas.addEventListener("mousemove", (evt) => {
  if (!state.drawing) return;
  const point = screenToImage(evt);
  state.drawing.rect = box(
    state.drawing.start.x,
    state.drawing.start.y,
    point.x - state.drawing.start.x,
    point.y - state.drawing.start.y,
  );
  draw();
});

canvas.addEventListener("mouseup", () => {
  if (!state.drawing) return;
  const rect = state.drawing.rect;
  if (rect.width > 2 && rect.height > 2) {
    if (state.drawing.mode === "panel") state.panelBox = rect;
    if (state.drawing.mode === "logo") state.logoBox = rect;
    if (state.drawing.mode === "button") {
      const button = selectedButton();
      if (button) button.bbox_template_coordinates = rect;
    }
  }
  state.drawing = null;
  refresh();
});

canvas.addEventListener("click", (evt) => {
  if (state.drawing) return;
  const button = hitTestButton(screenToImage(evt));
  if (button) {
    readForm();
    state.selectedButtonId = button.localId;
    refresh();
  }
});

els.imageInput.addEventListener("change", (evt) => {
  const file = evt.target.files?.[0];
  if (!file) return;
  const img = new Image();
  img.onload = () => {
    state.image = img;
    state.imageName = file.name;
    state.imageWidth = img.naturalWidth;
    state.imageHeight = img.naturalHeight;
    state.scale = Math.min(1, 960 / state.imageWidth);
    deriveIds();
    refresh();
  };
  img.src = URL.createObjectURL(file);
});

els.fitImage.addEventListener("click", () => {
  if (!state.image) return;
  state.scale = Math.min(1, 960 / state.imageWidth);
  refresh();
});

els.newButton.addEventListener("click", () => {
  readForm();
  const button = defaultButton();
  state.buttons.push(button);
  state.selectedButtonId = button.localId;
  els.drawMode.value = "button";
  refresh();
});

els.deleteSelected.addEventListener("click", () => {
  const index = selectedButtonIndex();
  if (index >= 0) {
    state.buttons.splice(index, 1);
    state.selectedButtonId = state.buttons[index]?.localId || state.buttons[index - 1]?.localId || null;
  } else if (els.drawMode.value === "logo") {
    state.logoBox = null;
  } else if (els.drawMode.value === "panel") {
    state.panelBox = null;
  }
  refresh();
});

for (const input of Object.values(fields)) {
  input.addEventListener("input", refresh);
  input.addEventListener("change", refresh);
}

document.getElementById("copyJson").addEventListener("click", async () => {
  updateExport("json");
  await navigator.clipboard.writeText(els.exportOutput.value);
});

document.getElementById("copySql").addEventListener("click", async () => {
  updateExport("sql");
  await navigator.clipboard.writeText(els.exportOutput.value);
});

document.getElementById("downloadJson").addEventListener("click", () => {
  updateExport("json");
  const blob = new Blob([els.exportOutput.value], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${fields.templateCode.value || "silvertech_template"}.json`;
  link.click();
});

els.exportOutput.addEventListener("focus", () => updateExport("json"));

els.saveDraft.addEventListener("click", () => {
  readForm();
  const form = {};
  for (const [key, input] of Object.entries(fields)) form[key] = input.value;
  localStorage.setItem(
    "silvertech_label_draft",
    JSON.stringify({
      form,
      imageName: state.imageName,
      imageWidth: state.imageWidth,
      imageHeight: state.imageHeight,
      panelBox: state.panelBox,
      logoBox: state.logoBox,
      buttons: state.buttons,
      selectedButtonId: state.selectedButtonId,
    }),
  );
});

els.loadDraft.addEventListener("click", () => {
  const raw = localStorage.getItem("silvertech_label_draft");
  if (!raw) return;
  const draft = JSON.parse(raw);
  for (const [key, value] of Object.entries(draft.form || {})) {
    if (fields[key]) fields[key].value = value;
  }
  state.imageName = draft.imageName || "";
  state.imageWidth = draft.imageWidth || 0;
  state.imageHeight = draft.imageHeight || 0;
  state.panelBox = draft.panelBox || null;
  state.logoBox = draft.logoBox || null;
  state.buttons = draft.buttons || [];
  state.selectedButtonId = draft.selectedButtonId || state.buttons[0]?.localId || null;
  refresh();
});

els.clearDraft.addEventListener("click", () => {
  if (!confirm("Clear the current labeling data?")) return;
  localStorage.removeItem("silvertech_label_draft");
  for (const input of Object.values(fields)) {
    if (input.tagName === "SELECT") continue;
    input.value = "";
  }
  fields.version.value = "1";
  state.panelBox = null;
  state.logoBox = null;
  state.buttons = [];
  state.selectedButtonId = null;
  refresh();
});

// ── Import JSON ───────────────────────────────────────────────────────────────
document.getElementById("importJsonInput").addEventListener("change", (evt) => {
  const file = evt.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    let data;
    try {
      data = JSON.parse(e.target.result);
    } catch {
      alert("Invalid JSON file.");
      return;
    }

    const device   = data.device   || {};
    const template = data.template || {};
    const buttons  = data.buttons  || [];

    // Populate device fields
    if (device.brand)           fields.brand.value           = device.brand;
    if (device.appliance_type)  fields.applianceType.value   = device.appliance_type;
    if (device.model_name)      fields.modelName.value       = device.model_name;
    if (device.display_name)    fields.displayName.value     = device.display_name;
    if (device.id)              fields.deviceId.value        = device.id;
    if (device.status)          fields.deviceStatus.value    = device.status;

    // Populate template fields
    if (template.template_code)             fields.templateCode.value     = template.template_code;
    if (template.template_image_url)        fields.templateImageUrl.value = template.template_image_url;
    if (template.feature_descriptor_path)   fields.descriptorPath.value   = template.feature_descriptor_path;
    if (template.id)                        fields.templateId.value       = template.id;
    if (template.version)                   fields.version.value          = template.version;
    if (template.status)                    fields.templateStatus.value   = template.status;

    // Populate bboxes
    state.panelBox = template.panel_bbox || null;
    state.logoBox  = template.logo_bbox  || null;

    // Populate buttons — add localId for internal tracking
    state.buttons = buttons.map((b) => ({
      localId: crypto.randomUUID(),
      button_id: b.button_id || "",
      label: b.label || "",
      vietnamese_name: b.vietnamese_name || "",
      function_description: b.function_description || "",
      button_type: b.button_type || "physical",
      bbox_template_coordinates: b.bbox_template_coordinates || null,
      polygon_template_coordinates: b.polygon_template_coordinates || null,
    }));
    state.selectedButtonId = state.buttons[0]?.localId || null;

    evt.target.value = ""; // allow re-importing same file
    refresh();
    alert(`Imported ${buttons.length} buttons. panel_bbox ${state.panelBox ? "✓" : "missing"}, logo_bbox ${state.logoBox ? "✓" : "missing"}.\n\nNow load the matching image to see all bboxes drawn.`);
  };
  reader.readAsText(file);
});

refresh();
