const emotions = ["fear", "anger", "joy", "sadness", "trust", "distrust", "surprise", "interest"];
const defaultVisibleEmotions = ["fear", "anger", "joy", "trust"];
const colors = {
  fear: "#7357b8",
  anger: "#b24747",
  joy: "#d49117",
  sadness: "#2f6fbd",
  trust: "#2f8f5b",
  distrust: "#4d5b6d",
  surprise: "#248997",
  interest: "#b5527b"
};

const fallbackTimeline = {
  schema_version: "manyu.timeline.v0.1",
  source: "embedded sample",
  emotions,
  agents: ["agent_demo"],
  turns: [
    {
      index: 1,
      agent_id: "agent_demo",
      event_id: "sample_1",
      event_type: "social_feedback",
      summary: "A trusted user rejects a plan constructively and asks for a simpler version.",
      pathway: "fast",
      state_revision: 1,
      post_state: { fear: 0.08, anger: 0.078, joy: 0.12, sadness: 0.0775, trust: 0.24, distrust: 0.02, surprise: 0.04, interest: 0.23 },
      appraisal_delta: { anger: 0.028, sadness: 0.0175, trust: 0.04, distrust: -0.03, interest: 0.05 },
      perceived_affects: { trust: 0.168, interest: 0.161, joy: 0.084 },
      felt_quality: ["open"],
      activation: 0.111,
      interoception_confidence: 0.7,
      appraisal_dimensions: [
        { dimension: "goal_congruence", value: -0.35, confidence: 0.93 },
        { dimension: "social_affiliation", value: 0.52, confidence: 0.93 }
      ],
      action_tendency: { action_class: "revise_and_seek_clarification", strength: 0.58 },
      reason_codes: ["feedback_obstructs_goal", "trusted_source"],
      arbitration: { disposition: "ACT_FAST", reason_codes: ["low_consequence"], constraints: ["no_sentience_claim", "do_not_expand_authority"] }
    }
  ]
};

let timeline = fallbackTimeline;
let selectedAgent = "agent_demo";
let selectedTurn = 0;
let activeEmotions = new Set(defaultVisibleEmotions);

const chart = document.getElementById("chart");
const ctx = chart.getContext("2d");
const sourceLabel = document.getElementById("sourceLabel");
const agentTabs = document.getElementById("agentTabs");
const legend = document.getElementById("legend");
const turnList = document.getElementById("turnList");
const turnCount = document.getElementById("turnCount");
const detail = document.getElementById("detail");

document.getElementById("sampleButton").addEventListener("click", () => {
  loadTimeline(fallbackTimeline);
});

document.getElementById("fileInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  loadTimeline(JSON.parse(text));
});

async function tryLoadDefault() {
  try {
    const response = await fetch("timeline.json", { cache: "no-store" });
    if (response.ok) {
      loadTimeline(await response.json());
      return;
    }
  } catch (_error) {
    // Opening from file:// usually blocks fetch; the embedded sample keeps the UI usable.
  }
  loadTimeline(fallbackTimeline);
}

function loadTimeline(next) {
  timeline = normalizeTimeline(next);
  selectedAgent = timeline.agents[0] || "agent_demo";
  selectedTurn = 0;
  resetActiveEmotions();
  render();
}

function normalizeTimeline(raw) {
  const turns = Array.isArray(raw.turns) ? raw.turns : [];
  const agents = raw.agents && raw.agents.length ? raw.agents : [...new Set(turns.map((turn) => turn.agent_id))];
  return {
    ...raw,
    emotions: raw.emotions && raw.emotions.length ? raw.emotions : emotions,
    agents,
    turns
  };
}

function turnsForAgent() {
  return timeline.turns.filter((turn) => turn.agent_id === selectedAgent);
}

function resetActiveEmotions() {
  const available = new Set(timeline.emotions);
  const defaults = defaultVisibleEmotions.filter((emotion) => available.has(emotion));
  activeEmotions = new Set(defaults.length ? defaults : timeline.emotions.slice(0, 4));
}

function visibleEmotions() {
  return timeline.emotions.filter((emotion) => activeEmotions.has(emotion));
}

function render() {
  sourceLabel.textContent = `${timeline.source || "timeline"} - ${timeline.turns.length} turns - ${timeline.agents.length} agent${timeline.agents.length === 1 ? "" : "s"}`;
  renderTabs();
  renderLegend();
  renderChart();
  renderTurns();
  renderDetail();
}

function renderTabs() {
  agentTabs.innerHTML = "";
  for (const agent of timeline.agents) {
    const button = document.createElement("button");
    button.className = `tab${agent === selectedAgent ? " active" : ""}`;
    button.textContent = agent;
    button.addEventListener("click", () => {
      selectedAgent = agent;
      selectedTurn = 0;
      render();
    });
    agentTabs.appendChild(button);
  }
}

function renderLegend() {
  legend.innerHTML = "";
  for (const emotion of timeline.emotions) {
    const item = document.createElement("label");
    const isActive = activeEmotions.has(emotion);
    item.className = `legendItem${isActive ? " active" : ""}`;
    item.innerHTML = `
      <input type="checkbox" ${isActive ? "checked" : ""} />
      <span class="swatch" style="background:${colors[emotion] || "#333"}"></span>
      <span>${emotion}</span>
    `;
    item.querySelector("input").addEventListener("change", (event) => {
      if (event.target.checked) activeEmotions.add(emotion);
      else activeEmotions.delete(emotion);
      renderLegend();
      renderChart();
    });
    legend.appendChild(item);
  }
}

function renderChart() {
  const dpr = window.devicePixelRatio || 1;
  const rect = chart.getBoundingClientRect();
  chart.width = Math.max(600, Math.floor(rect.width * dpr));
  chart.height = Math.floor(380 * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const width = rect.width;
  const height = 380;
  const pad = { left: 46, right: 18, top: 20, bottom: 56 };
  const turns = turnsForAgent();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfe";
  ctx.fillRect(0, 0, width, height);
  drawGrid(width, height, pad);
  if (!turns.length) {
    ctx.fillStyle = "#657085";
    ctx.fillText("No turns for this agent.", pad.left, pad.top + 24);
    return;
  }
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const xFor = (index) => pad.left + (turns.length === 1 ? plotW / 2 : (index / (turns.length - 1)) * plotW);
  const yFor = (value) => pad.top + (1 - clamp(value)) * plotH;
  for (const emotion of visibleEmotions()) {
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = colors[emotion] || "#333";
    turns.forEach((turn, idx) => {
      const x = xFor(idx);
      const y = yFor(turn.post_state?.[emotion] ?? 0);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    turns.forEach((turn, idx) => {
      const x = xFor(idx);
      const y = yFor(turn.post_state?.[emotion] ?? 0);
      ctx.beginPath();
      ctx.fillStyle = colors[emotion] || "#333";
      ctx.arc(x, y, idx === selectedTurn ? 3.5 : 2.5, 0, Math.PI * 2);
      ctx.fill();
    });
  }
  for (const emotion of visibleEmotions()) {
    let started = false;
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 5]);
    ctx.globalAlpha = 0.72;
    ctx.strokeStyle = colors[emotion] || "#333";
    turns.forEach((turn, idx) => {
      const perceivedValue = turn.perceived_affects?.[emotion];
      if (perceivedValue === undefined || perceivedValue === null) {
        started = false;
        return;
      }
      const x = xFor(idx);
      const y = yFor(perceivedValue);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.setLineDash([]);
    turns.forEach((turn, idx) => {
      const perceivedValue = turn.perceived_affects?.[emotion];
      if (perceivedValue === undefined || perceivedValue === null) return;
      const x = xFor(idx);
      const y = yFor(perceivedValue);
      ctx.beginPath();
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = colors[emotion] || "#333";
      ctx.lineWidth = 1.5;
      ctx.arc(x, y, idx === selectedTurn ? 4 : 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });
  }
  ctx.globalAlpha = 1;
  ctx.setLineDash([]);
  turns.forEach((turn, idx) => {
    const x = xFor(idx);
    ctx.strokeStyle = idx === selectedTurn ? "#172033" : "#c9d0dc";
    ctx.lineWidth = idx === selectedTurn ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + plotH);
    ctx.stroke();
    ctx.fillStyle = idx === selectedTurn ? "#172033" : "#657085";
    ctx.font = idx === selectedTurn ? "600 12px Segoe UI, Arial" : "12px Segoe UI, Arial";
    ctx.textAlign = "center";
    ctx.fillText(`T${turn.index}`, x, pad.top + plotH + 20);
    if (turns.length <= 8) {
      ctx.fillText(shortEventLabel(turn.event_type), x, pad.top + plotH + 37);
    }
  });
  ctx.textAlign = "left";
}

function drawGrid(width, height, pad) {
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  ctx.strokeStyle = "#e1e5ec";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#657085";
  ctx.font = "12px Segoe UI, Arial";
  [0, 0.25, 0.5, 0.75, 1].forEach((value) => {
    const y = pad.top + (1 - value) * plotH;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    ctx.fillText(value.toFixed(2), 8, y + 4);
  });
  ctx.strokeStyle = "#bfc7d3";
  ctx.strokeRect(pad.left, pad.top, plotW, plotH);
  ctx.fillStyle = "#657085";
  ctx.font = "12px Segoe UI, Arial";
  ctx.fillText("turns", pad.left, height - 10);
}

function renderTurns() {
  const turns = turnsForAgent();
  turnCount.textContent = `${turns.length} turns`;
  turnList.innerHTML = "";
  turns.forEach((turn, idx) => {
    const button = document.createElement("button");
    button.className = `turn${idx === selectedTurn ? " active" : ""}`;
    button.innerHTML = `
      <div class="turnTitle"><span>${turn.index}. ${turn.event_type}</span><span>${turn.arbitration?.disposition || ""}</span></div>
      <div class="turnSummary">${escapeHtml(turn.summary)}</div>
      <div class="pillRow">
        ${(turn.felt_quality || []).map((quality) => `<span class="pill">${escapeHtml(quality)}</span>`).join("")}
        <span class="pill">${turn.pathway}</span>
      </div>
    `;
    button.addEventListener("click", () => {
      selectedTurn = idx;
      render();
    });
    turnList.appendChild(button);
  });
}

function renderDetail() {
  const turn = turnsForAgent()[selectedTurn];
  if (!turn) {
    detail.innerHTML = `<p class="muted">No turn selected.</p>`;
    return;
  }
  detail.innerHTML = `
    <section class="detailSection">
      <h2>${turn.index}. ${escapeHtml(turn.event_type)}</h2>
      <p class="turnSummary">${escapeHtml(turn.summary)}</p>
      <dl class="kv">
        <dt>Agent</dt><dd>${escapeHtml(turn.agent_id)}</dd>
        <dt>Revision</dt><dd>${turn.state_revision}</dd>
        <dt>Pathway</dt><dd>${turn.pathway}</dd>
        <dt>Disposition</dt><dd>${escapeHtml(turn.arbitration?.disposition || "")}</dd>
      </dl>
    </section>
    <section class="detailSection">
      <h2>Perceived State</h2>
      <p class="turnSummary">Dashed chart lines show this partial interoceptive estimate. Missing emotions are not visible to the agent on that turn.</p>
      <dl class="kv">
        <dt>Felt quality</dt><dd>${(turn.felt_quality || []).map(escapeHtml).join(", ") || "none"}</dd>
        <dt>Activation</dt><dd>${formatNumber(turn.activation)}</dd>
        <dt>Confidence</dt><dd>${formatNumber(turn.interoception_confidence)}</dd>
      </dl>
      ${renderBars(turn.perceived_affects || {})}
    </section>
    <section class="detailSection">
      <h2>Authoritative Affect</h2>
      ${renderBars(turn.post_state || {})}
    </section>
    <section class="detailSection">
      <h2>Delta</h2>
      ${renderBars(turn.appraisal_delta || {}, true)}
    </section>
    <section class="detailSection">
      <h2>Why</h2>
      <div class="pillRow">${(turn.reason_codes || []).map((code) => `<span class="pill">${escapeHtml(code)}</span>`).join("")}</div>
      <dl class="kv">
        ${(turn.appraisal_dimensions || []).map((dimension) => `
          <dt>${escapeHtml(dimension.dimension)}</dt>
          <dd>${formatNumber(dimension.value)} - confidence ${formatNumber(dimension.confidence)}</dd>
        `).join("")}
      </dl>
    </section>
  `;
}

function renderBars(values, signed = false) {
  return Object.entries(values).map(([name, value]) => {
    const width = signed ? Math.min(1, Math.abs(value) * 4) : clamp(value);
    const color = signed && value < 0 ? "#4d5b6d" : (colors[name] || "#2f6fbd");
    return `
      <div class="barLabel">${escapeHtml(name)} <span class="muted">${formatNumber(value)}</span></div>
      <div class="bar"><span style="width:${width * 100}%;background:${color}"></span></div>
    `;
  }).join("");
}

function clamp(value) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

function formatNumber(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "n/a";
  return Number(value).toFixed(3);
}

function shortEventLabel(value) {
  return String(value || "").replace("goal_", "").replace("social_", "social ").replace("_", " ").slice(0, 12);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}

tryLoadDefault();
