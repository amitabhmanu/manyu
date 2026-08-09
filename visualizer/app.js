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
  ],
  belief_evidence: [
    {
      evidence_id: "bev_sample_1",
      agent_id: "agent_demo",
      source_type: "trace",
      source_id: "trace_sample_1",
      summary: "Constructive rejection became evidence that revision can preserve collaboration.",
      trust_class: "trusted_system",
      affective_salience: 0.46,
      epistemic_weight: 0.72,
      created_at: "2026-07-15T00:00:00Z"
    }
  ],
  beliefs: [
    {
      belief_id: "bel_sample_1",
      agent_id: "agent_demo",
      proposition: "Feedback that preserves trust is a revision signal in Manyu's interaction model, not a threat.",
      belief_type: "interaction_pattern",
      scope: "human_agent_interaction",
      confidence: 0.68,
      stability: 0.32,
      valence: 0.35,
      source_mix: { manyu_experience: 0.8, reflection: 0.2 },
      evidence_ids: ["bev_sample_1"],
      contradicts: [],
      status: "active",
      uncertainty: "Only one sample interaction is represented.",
      created_at: "2026-07-15T00:00:05Z",
      updated_at: "2026-07-15T00:00:05Z"
    }
  ],
  worldview_stances: [
    {
      worldview_id: "wv_sample_collaboration",
      agent_id: "agent_demo",
      theme: "collaboration",
      stance: "On collaboration, Manyu sees trust-preserving revision as more reliable than defensiveness.",
      supporting_belief_ids: ["bel_sample_1"],
      confidence: 0.68,
      maturity: "developing",
      expression_guidance: "Speak as a bounded Manyu-specific view with provenance and uncertainty.",
      created_at: "2026-07-15T00:00:08Z",
      updated_at: "2026-07-15T00:00:08Z"
    }
  ],
  inner_voice_frames: [
    {
      voice_id: "voice_sample_1",
      agent_id: "agent_demo",
      state_revision: 1,
      source_interoception_id: "view_sample_1",
      source_event_id: "sample_1",
      mood_label: "open_repair",
      utterance: "Revision looks useful here. Keep trust visible, ask for the missing shape, and do not over-defend the first plan.",
      confidence: 0.66,
      influence: { caution: 0.22, curiosity: 0.48, trust_openness: 0.52, skepticism: 0.12, repair_orientation: 0.58, risk_aversion: 0.16, response_pacing: 0.32 },
      safety_status: "accepted",
      safety_notes: [],
      supporting_belief_ids: ["bel_sample_1"],
      supporting_worldview_ids: ["wv_sample_collaboration"]
    }
  ],
  mood_states: [
    {
      mood_id: "mood_sample_1",
      agent_id: "agent_demo",
      state_revision: 1,
      label: "open_repair",
      valence: 0.36,
      arousal: 0.58,
      momentum: 0.2,
      influence: { caution: 0.22, curiosity: 0.48, trust_openness: 0.52, skepticism: 0.12, repair_orientation: 0.58, risk_aversion: 0.16, response_pacing: 0.32 },
      supporting_voice_ids: ["voice_sample_1"],
      status: "active"
    }
  ]
};

let timeline = fallbackTimeline;
let selectedAgent = "agent_demo";
let selectedTurn = 0;
let selectedBeliefId = null;
let activeEmotions = new Set(defaultVisibleEmotions);

const chart = document.getElementById("chart");
const ctx = chart.getContext("2d");
const sourceLabel = document.getElementById("sourceLabel");
const overview = document.getElementById("overview");
const agentTabs = document.getElementById("agentTabs");
const legend = document.getElementById("legend");
const turnList = document.getElementById("turnList");
const turnCount = document.getElementById("turnCount");
const beliefCount = document.getElementById("beliefCount");
const moodCount = document.getElementById("moodCount");
const moodLane = document.getElementById("moodLane");
const worldview = document.getElementById("worldview");
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
  selectedBeliefId = null;
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
    turns,
    belief_evidence: Array.isArray(raw.belief_evidence) ? raw.belief_evidence : [],
    beliefs: Array.isArray(raw.beliefs) ? raw.beliefs : [],
    worldview_stances: Array.isArray(raw.worldview_stances) ? raw.worldview_stances : [],
    opinion_expressions: Array.isArray(raw.opinion_expressions) ? raw.opinion_expressions : [],
    inner_voice_frames: Array.isArray(raw.inner_voice_frames) ? raw.inner_voice_frames : [],
    mood_states: Array.isArray(raw.mood_states) ? raw.mood_states : []
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

function evidenceForAgent() {
  return timeline.belief_evidence.filter((item) => item.agent_id === selectedAgent);
}

function beliefsForAgent() {
  return timeline.beliefs.filter((belief) => belief.agent_id === selectedAgent);
}

function worldviewsForAgent() {
  return timeline.worldview_stances.filter((stance) => stance.agent_id === selectedAgent);
}

function voicesForAgent() {
  return timeline.inner_voice_frames.filter((voice) => voice.agent_id === selectedAgent);
}

function moodsForAgent() {
  return timeline.mood_states.filter((mood) => mood.agent_id === selectedAgent);
}

function voiceForTurn(turn) {
  return voicesForAgent().find((voice) => voice.source_event_id === turn.event_id || voice.state_revision === turn.state_revision);
}

function moodForTurn(turn) {
  return moodsForAgent().find((mood) => mood.state_revision === turn.state_revision);
}

function evidenceById() {
  return Object.fromEntries(evidenceForAgent().map((item) => [item.evidence_id, item]));
}

function beliefsForTurn(turn) {
  const byId = evidenceById();
  return beliefsForAgent().filter((belief) => (belief.evidence_ids || []).some((id) => {
    const evidence = byId[id];
    if (!evidence) return false;
    return evidence.source_id === turn.trace_id || evidence.source_id === turn.event_id || evidence.source_id === `trace_${turn.event_id}`;
  }));
}

function render() {
  sourceLabel.textContent = `${timeline.source || "timeline"} - ${timeline.turns.length} turns - ${timeline.agents.length} agent${timeline.agents.length === 1 ? "" : "s"}`;
  renderOverview();
  renderTabs();
  renderLegend();
  renderChart();
  renderMoodLane();
  renderWorldview();
  renderTurns();
  renderDetail();
}

function renderOverview() {
  const turns = turnsForAgent();
  const beliefs = beliefsForAgent();
  const stances = worldviewsForAgent();
  const moods = moodsForAgent();
  const latest = turns[turns.length - 1];
  const topEmotion = latest?.post_state ? Object.entries(latest.post_state).sort((a, b) => b[1] - a[1])[0] : null;
  const avgBeliefConfidence = beliefs.length ? beliefs.reduce((sum, belief) => sum + Number(belief.confidence || 0), 0) / beliefs.length : 0;
  overview.innerHTML = [
    metricCard("turns", turns.length),
    metricCard("top affect", topEmotion ? `${topEmotion[0]} ${formatNumber(topEmotion[1])}` : "n/a"),
    metricCard("beliefs", beliefs.length),
    metricCard("worldviews", stances.length),
    metricCard("active mood", moods[0]?.label || "n/a"),
    metricCard("belief confidence", beliefs.length ? formatNumber(avgBeliefConfidence) : "n/a")
  ].join("");
}

function metricCard(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
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
  drawBeliefMarkers(turns, xFor, pad, plotH);
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

function drawBeliefMarkers(turns, xFor, pad, plotH) {
  const y = pad.top + plotH + 47;
  turns.forEach((turn, idx) => {
    const related = beliefsForTurn(turn);
    if (!related.length) return;
    const x = xFor(idx);
    ctx.save();
    ctx.translate(x, y);
    ctx.fillStyle = related.some((belief) => belief.status === "contested") ? "#b24747" : "#172033";
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, -6);
    ctx.lineTo(6, 0);
    ctx.lineTo(0, 6);
    ctx.lineTo(-6, 0);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    if (related.length > 1) {
      ctx.fillStyle = "#172033";
      ctx.font = "600 10px Segoe UI, Arial";
      ctx.fillText(String(related.length), 8, 3);
    }
    ctx.restore();
  });
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
    const relatedBeliefs = beliefsForTurn(turn);
    const button = document.createElement("button");
    button.className = `turn${idx === selectedTurn ? " active" : ""}`;
    button.innerHTML = `
      <div class="turnTitle"><span>${turn.index}. ${turn.event_type}</span><span>${turn.arbitration?.disposition || ""}</span></div>
      <div class="turnSummary">${escapeHtml(turn.summary)}</div>
      <div class="pillRow">
        ${(turn.felt_quality || []).map((quality) => `<span class="pill">${escapeHtml(quality)}</span>`).join("")}
        <span class="pill">${turn.pathway}</span>
        ${relatedBeliefs.map((belief) => `<span class="pill beliefPill">${escapeHtml(belief.belief_type)}</span>`).join("")}
      </div>
    `;
    button.addEventListener("click", () => {
      selectedTurn = idx;
      render();
    });
    turnList.appendChild(button);
  });
}

function renderWorldview() {
  const beliefs = beliefsForAgent();
  const stances = worldviewsForAgent();
  beliefCount.textContent = `${beliefs.length} beliefs`;
  if (!beliefs.length && !stances.length) {
    worldview.innerHTML = `<p class="emptyState">No belief or worldview records in this timeline yet.</p>`;
    return;
  }
  const lanes = stances.map((stance) => `
    <article class="stance">
      <div class="stanceHeader">
        <span>${escapeHtml(stance.theme)}</span>
        <strong>${formatNumber(stance.confidence)}</strong>
      </div>
      <p>${escapeHtml(stance.stance)}</p>
      <div class="maturity">${escapeHtml(stance.maturity || "developing")}</div>
    </article>
  `).join("");
  const stream = beliefs
    .slice()
    .sort((a, b) => String(a.created_at || "").localeCompare(String(b.created_at || "")))
    .map((belief, index) => beliefCard(belief, index))
    .join("");
  worldview.innerHTML = `
    <div class="stanceGrid">${lanes || `<p class="emptyState">Run worldview review to synthesize stances.</p>`}</div>
    <div class="beliefStream">${stream}</div>
  `;
  worldview.querySelectorAll("[data-belief-id]").forEach((node) => {
    node.addEventListener("click", () => {
      selectedBeliefId = node.getAttribute("data-belief-id");
      renderWorldview();
      renderDetail();
    });
  });
}

function renderMoodLane() {
  const turns = turnsForAgent();
  const voices = voicesForAgent();
  const moods = moodsForAgent();
  moodCount.textContent = `${voices.length} voices - ${moods.length} moods`;
  if (!voices.length && !moods.length) {
    moodLane.innerHTML = `<p class="emptyState">No inner voice or mood records in this timeline yet.</p>`;
    return;
  }
  moodLane.innerHTML = turns.map((turn, idx) => {
    const voice = voiceForTurn(turn);
    const mood = moodForTurn(turn);
    const selected = idx === selectedTurn ? " active" : "";
    return `
      <button class="moodCard${selected}" data-turn-index="${idx}">
        <div class="moodHeader">
          <span>T${turn.index}</span>
          <strong>${escapeHtml(mood?.label || voice?.mood_label || "no mood")}</strong>
        </div>
        <p>${escapeHtml(voice?.utterance || "No inner voice frame linked to this turn.")}</p>
        ${renderInfluenceMini(mood?.influence || voice?.influence || {})}
      </button>
    `;
  }).join("");
  moodLane.querySelectorAll("[data-turn-index]").forEach((node) => {
    node.addEventListener("click", () => {
      selectedTurn = Number(node.getAttribute("data-turn-index"));
      render();
    });
  });
}

function renderInfluenceMini(values) {
  const keys = ["caution", "curiosity", "trust_openness", "skepticism", "repair_orientation", "response_pacing"];
  return `<div class="influenceGrid">${keys.map((key) => `
    <div>
      <span>${escapeHtml(key.replace("_", " "))}</span>
      <div class="miniBar"><i style="width:${clamp(values[key]) * 100}%"></i></div>
    </div>
  `).join("")}</div>`;
}

function beliefCard(belief, index) {
  const active = belief.belief_id === selectedBeliefId ? " active" : "";
  return `
    <button class="beliefCard${active}" data-belief-id="${escapeHtml(belief.belief_id)}">
      <span class="beliefIndex">${index + 1}</span>
      <span class="beliefType">${escapeHtml(belief.belief_type)}</span>
      <strong>${escapeHtml(belief.status)}</strong>
      <p>${escapeHtml(belief.proposition)}</p>
      <div class="confidenceTrack"><span style="width:${clamp(belief.confidence) * 100}%"></span></div>
    </button>
  `;
}

function renderDetail() {
  const turn = turnsForAgent()[selectedTurn];
  const selectedBelief = beliefsForAgent().find((belief) => belief.belief_id === selectedBeliefId);
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
    ${renderMoodDetail(turn)}
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
    ${renderBeliefDetail(selectedBelief)}
  `;
}

function renderMoodDetail(turn) {
  const voice = voiceForTurn(turn);
  const mood = moodForTurn(turn);
  if (!voice && !mood) return "";
  return `
    <section class="detailSection">
      <h2>Inner Voice & Mood</h2>
      ${voice ? `<p class="turnSummary">${escapeHtml(voice.utterance)}</p>` : `<p class="turnSummary">No inner voice linked to this turn.</p>`}
      <dl class="kv">
        <dt>Voice mood</dt><dd>${escapeHtml(voice?.mood_label || "n/a")}</dd>
        <dt>Safety</dt><dd>${escapeHtml(voice?.safety_status || "n/a")}</dd>
        <dt>Active mood</dt><dd>${escapeHtml(mood?.label || "n/a")}</dd>
        <dt>Momentum</dt><dd>${formatNumber(mood?.momentum)}</dd>
        <dt>Arousal</dt><dd>${formatNumber(mood?.arousal)}</dd>
      </dl>
      <h2 class="subhead">Influence</h2>
      ${renderBars(mood?.influence || voice?.influence || {})}
    </section>
  `;
}

function renderBeliefDetail(belief) {
  if (!belief) {
    const related = beliefsForTurn(turnsForAgent()[selectedTurn] || {});
    if (!related.length) return "";
    belief = related[0];
  }
  const byId = evidenceById();
  return `
    <section class="detailSection">
      <h2>Belief Focus</h2>
      <p class="turnSummary">${escapeHtml(belief.proposition)}</p>
      <dl class="kv">
        <dt>Status</dt><dd>${escapeHtml(belief.status)}</dd>
        <dt>Type</dt><dd>${escapeHtml(belief.belief_type)}</dd>
        <dt>Scope</dt><dd>${escapeHtml(belief.scope)}</dd>
        <dt>Confidence</dt><dd>${formatNumber(belief.confidence)}</dd>
        <dt>Stability</dt><dd>${formatNumber(belief.stability)}</dd>
        <dt>Valence</dt><dd>${formatNumber(belief.valence)}</dd>
      </dl>
      <h2 class="subhead">Source Mix</h2>
      ${renderBars(belief.source_mix || {})}
      <h2 class="subhead">Evidence</h2>
      ${(belief.evidence_ids || []).map((id) => {
        const evidence = byId[id];
        return `<div class="evidenceItem"><strong>${escapeHtml(id)}</strong><p>${escapeHtml(evidence?.summary || "Evidence not present in this export.")}</p></div>`;
      }).join("")}
      ${belief.uncertainty ? `<p class="turnSummary">${escapeHtml(belief.uncertainty)}</p>` : ""}
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
