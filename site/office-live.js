/* Verified GitHub Actions role evidence for the static VideoForge office.
 * Public REST endpoints only; never asks for tokens, writes or starts work.
 * A completed backend role != an autonomous AI agent.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.VideoForgeLive = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";
  const REPO = "HelioConde/video-forge-ia";
  const API = "https://api.github.com/repos/" + REPO;
  const PREFIX = "VideoForge Pipeline / ";
  const ROLES = Object.freeze({
    diretor: "Briefing validado pelo pipeline",
    roteirista: "Roteiro recebido e validado (não gerado autonomamente)",
    narrador: "Narração Edge TTS",
    artista: "Imagens geradas pela API integrada",
    animador: "Movimentos de câmera e composição preparados",
    editor: "MP4 renderizado com Remotion",
    revisor: "Verificação técnica do MP4 (não aprovação editorial)"
  });
  const ALLOWED_STATUSES = new Set(["queued", "in_progress", "completed"]);

  function runUrl(id) {
    return "https://github.com/" + REPO + "/actions/runs/" + String(id);
  }
  function usableRun(run) {
    return run && Number.isSafeInteger(run.id) && run.id > 0 &&
      typeof run.head_sha === "string" && /^[a-f0-9]{40}$/.test(run.head_sha) &&
      ALLOWED_STATUSES.has(run.status) && (run.event === "push" || run.event === "workflow_dispatch");
  }
  function readEvidence(run, checkRuns) {
    if (!usableRun(run)) return null;
    const rows = {};
    for (const item of Array.isArray(checkRuns) ? checkRuns : []) {
      if (!item || typeof item.name !== "string" || !item.name.startsWith(PREFIX)) continue;
      const role = item.name.slice(PREFIX.length);
      if (!(role in ROLES)) continue;
      const match = /^vf-autoeditor:([0-9]+):([a-z0-9]+(?:-[a-z0-9]+)*):([a-z]+)$/.exec(item.external_id || "");
      if (!match || match[1] !== String(run.id) || match[3] !== role) continue;
      if (item.head_sha !== run.head_sha || item.details_url !== runUrl(run.id)) continue;
      if (!["in_progress", "completed"].includes(item.status) || !Number.isSafeInteger(item.id)) continue;
      if (!rows[role] || rows[role].id < item.id) rows[role] = {
        id: item.id, role, channel: match[2],
        status: item.status,
        conclusion: item.conclusion === "success" ? "success" :
          item.conclusion === "failure" ? "failure" : null
      };
    }
    return {
      runId: run.id,
      url: runUrl(run.id),
      runStatus: run.status,
      runConclusion: run.conclusion || null,
      lastUpdate: run.updated_at || run.created_at || "",
      tasks: Object.values(rows)
    };
  }

  async function load(fetchImpl) {
    const get = fetchImpl || (typeof fetch === "function" && fetch);
    if (!get) throw new Error("FETCH_UNAVAILABLE");
    async function read(url) {
      const response = await get(url, {headers: {Accept: "application/vnd.github+json"}, cache: "no-store"});
      if (!response.ok) throw new Error("GITHUB_API_HTTP_ERROR");
      return response.json();
    }
    const runs = await read(API + "/actions/workflows/autoeditor-generator.yml/runs?branch=main&per_page=1");
    const run = runs && Array.isArray(runs.workflow_runs) ? runs.workflow_runs[0] : null;
    if (!usableRun(run)) return null;
    const checks = await read(API + "/commits/" + run.head_sha + "/check-runs?per_page=100");
    return readEvidence(run, checks && checks.check_runs);
  }

  function merge(snapshot, evidence) {
    if (!snapshot || !Array.isArray(snapshot.agentes)) throw new Error("INVALID_SNAPSHOT");
    const copy = JSON.parse(JSON.stringify(snapshot));
    if (!evidence || !evidence.runId || !Array.isArray(evidence.tasks)) return copy;
    const available = new Set((copy.canais || []).map(x => x.id));
    let matched = 0;
    for (const task of evidence.tasks) {
      if (!task || !(task.role in ROLES) || !available.has(task.channel)) continue;
      const agent = copy.agentes.find(x => x.id === task.role);
      if (!agent) continue;
      // Closed runs can never leave an agent incorrectly "working".
      const active = evidence.runStatus === "in_progress" && task.status === "in_progress";
      const failed = task.conclusion === "failure" || (task.status === "in_progress" && !active);
      agent.status = active ? "trabalhando" : failed ? "erro" :
        task.conclusion === "success" ? "concluido" : "aguardando";
      agent.tarefa = ROLES[task.role];
      agent.canal = task.channel;
      agent.execucao_pipeline = {
        origem: "github_checks", run_id: evidence.runId,
        evidence_url: evidence.url, work_type: "pipeline_task_not_autonomous_ai",
        concluded: task.status === "completed"
      };
      if (agent.conexao) {
        agent.conexao.eventos_observados = true;
        agent.conexao.pendencias = agent.conexao.pendencias.filter(x => x !== "Sem telemetria de execução comprovada");
      }
      matched++;
    }
    copy.telemetria = {
      source: "github_actions_checks",
      run_id: evidence.runId,
      run_url: evidence.url,
      status: evidence.runStatus,
      conclusion: evidence.runConclusion,
      recorded_roles: matched,
      last_update: evidence.lastUpdate
    };
    if (matched) copy.fonte = "eventos_backend";
    // Polling GitHub API does not constitute a realtime streaming connection.
    copy.tempo_real = false;
    return copy;
  }
  return {API, PREFIX, ROLES, load, readEvidence, merge};
});
