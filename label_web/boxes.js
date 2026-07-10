// label_web/boxes.js
// Shared by index.html (labelling) and review.html (admin review). Plain script,
// no modules: both pages load it with a <script src> before their own file.

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

function screenToImage(evt, canvas, scale) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (evt.clientX - rect.left) / scale,
    y: (evt.clientY - rect.top) / scale,
  };
}

function drawBox(ctx, rect, scale, color, label, active = false) {
  if (!rect) return;
  const x = rect.x * scale;
  const y = rect.y * scale;
  const w = rect.width * scale;
  const h = rect.height * scale;
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
