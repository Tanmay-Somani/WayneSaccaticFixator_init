const screen = document.getElementById("led-screen");
const canvas = document.getElementById("led-canvas");
const startBtn = document.getElementById("start-btn");

let ledPositions = null;
let activeLedId = null;

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const size = canvas.clientWidth;
  canvas.width = Math.max(1, Math.round(size * dpr));
  canvas.height = Math.max(1, Math.round(size * dpr));
}

function drawLed(ctx, x, y, r, lit) {
  if (lit) {
    const glow = ctx.createRadialGradient(x, y, r * 0.2, x, y, r * 3);
    glow.addColorStop(0, "rgba(255, 26, 26, 0.55)");
    glow.addColorStop(1, "rgba(255, 26, 26, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y, r * 3, 0, Math.PI * 2);
    ctx.fill();

    const core = ctx.createRadialGradient(x - r * 0.3, y - r * 0.35, r * 0.1, x, y, r);
    core.addColorStop(0, "#ffffff");
    core.addColorStop(0.35, "#ffd9d4");
    core.addColorStop(0.72, "#ff1a1a");
    core.addColorStop(1, "#6b0000");
    ctx.fillStyle = core;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  } else {
    const cap = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
    cap.addColorStop(0, "#3a4456");
    cap.addColorStop(0.55, "#232c3a");
    cap.addColorStop(1, "#151b25");
    ctx.fillStyle = cap;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "rgba(255, 255, 255, 0.09)";
    ctx.lineWidth = Math.max(1, r * 0.12);
    ctx.beginPath();
    ctx.arc(x, y, r * 0.86, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = "rgba(0, 0, 0, 0.55)";
    ctx.lineWidth = Math.max(1, r * 0.14);
    ctx.beginPath();
    ctx.arc(x, y, r * 0.98, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function renderBoard() {
  if (!ledPositions) return;
  resizeCanvas();
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const size = canvas.clientWidth;
  ctx.clearRect(0, 0, size, size);
  const r = Math.max(2, size * 0.0215);
  ledPositions.forEach((p) => {
    drawLed(ctx, p.x * size, p.y * size, r, p.id === activeLedId);
  });
}

function render(state) {
  if (state.led_positions) {
    ledPositions = state.led_positions;
  }
  if (state.active_led_id !== undefined) {
    activeLedId = state.active_led_id;
  }
  renderBoard();

  startBtn.textContent = state.running ? "STOP TEST" : "START TEST";
  startBtn.classList.toggle("stop", state.running);
}

async function fetchState() {
  try {
    const res = await fetch("/api/state");
    if (!res.ok) return;
    render(await res.json());
  } catch {
    /* server unreachable; keep last known state */
  }
}

async function post(path) {
  try {
    const res = await fetch(path, { method: "POST" });
    if (!res.ok) return;
    render((await res.json()).state);
  } catch {
    /* ignore */
  }
}

function onPadTouch(event) {
  event.preventDefault();
  const rect = screen.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width;
  const y = (event.clientY - rect.top) / rect.height;
  const clampedX = Math.min(1, Math.max(0, x));
  const clampedY = Math.min(1, Math.max(0, y));
  fetch("/api/touch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ x: clampedX, y: clampedY }),
  }).catch(() => {});
}

screen.addEventListener("pointerdown", onPadTouch);
startBtn.addEventListener("click", () => {
  const running = startBtn.classList.contains("stop");
  post(running ? "/api/session/stop" : "/api/session/start");
});

let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    resizeCanvas();
    renderBoard();
  }, 50);
});

if (window.ResizeObserver) {
  new ResizeObserver(() => renderBoard()).observe(canvas);
} else {
  window.addEventListener("resize", () => {
    resizeCanvas();
    renderBoard();
  });
}

fetchState();
setInterval(fetchState, 100);
