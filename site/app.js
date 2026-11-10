"use strict";

const LABELS = {
  nao_conectado: "Não conectado",
  aguardando: "Aguardando",
  trabalhando: "Trabalhando",
  revisao: "Em revisão",
  concluido: "Concluído",
  erro: "Erro"
};
const $ = (id) => document.getElementById(id);
const state = { snapshot: null, selected: "diretor", canal: "todos" };

function el(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = String(content);
  return node;
}
function avatar() {
  const node = el("span", "pixel-human");
  node.setAttribute("aria-hidden", "true");
  return node;
}
function active(status) {
  return ["trabalhando", "revisao"].includes(status);
}
function displayStatus(status) {
  return LABELS[status] || "Estado desconhecido";
}
function friendlyDate(iso) {
  if (!iso) return "Sem horário";
  const date = new Date(iso);
  return isNaN(date.getTime()) ? "Sem horário" : date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}
function renderInspector() {
  const snap = state.snapshot;
  if (!snap) return;
  const a = snap.agentes.find(x => x.id === state.selected) || snap.agentes[0];
  if (!a) return;
  $("agentIndex").textContent = "POSTO / " + String(snap.agentes.indexOf(a) + 1).padStart(2, "0");
  $("inspectorName").textContent = a.nome;
  $("inspectorRole").textContent = a.funcao;
  $("inspectorState").textContent = displayStatus(a.status);
  $("inspectorState").className = "inspector-state" + (active(a.status) ? " is-working" : "");
  $("inspectorTask").textContent = a.tarefa || "Nenhuma tarefa reportada";
  const ch = snap.canais.find(c => c.id === a.canal);
  $("inspectorChannel").textContent = ch ? ch.nome : "Não atribuído";
  const area = $("inspectorAvatar");
  area.replaceChildren(avatar());
  area.dataset.agent = a.id;
}
function renderAgents() {
  const snap = state.snapshot;
  const frag = document.createDocumentFragment();
  for (const a of snap.agentes) {
    const card = el("button", "desk");
    card.type = "button";
    card.dataset.agent = a.id;
    card.classList.toggle("is-selected", state.selected === a.id);
    card.classList.toggle("is-working", active(a.status));
    card.classList.toggle("is-waiting", a.status === "aguardando");
    card.setAttribute("aria-pressed", state.selected === a.id ? "true" : "false");
    card.setAttribute("aria-label", a.nome + ": " + displayStatus(a.status) + ". Abrir detalhes");
    card.append(el("span", "desk-monitor"), el("span", "desk-furniture"), avatar());
    card.append(el("span", "desk-name", a.nome), el("span", "desk-state", displayStatus(a.status)));
    card.addEventListener("click", () => {
      state.selected = a.id;
      renderAgents();
      renderInspector();
    });
    frag.append(card);
  }
  $("agentFloor").replaceChildren(frag);
}
function renderChannels() {
  const wrap = $("channelsList");
  const frag = document.createDocumentFragment();
  const list = state.canal === "todos" ? state.snapshot.canais : state.snapshot.canais.filter(c => c.id === state.canal);
  for (const c of list) {
    const card = el("article", "channel-card");
    card.append(el("span", "channel-icon", "▶"));
    card.append(el("strong", "", c.nome));
    card.append(el("span", "channel-sub", c.id + " · " + c.idioma));
    card.append(el("span", "channel-model", c.modelo));
    frag.append(card);
  }
  wrap.replaceChildren(frag);
}
function updateFilters() {
  const select = $("channelFilter");
  const previous = state.canal;
  select.replaceChildren(el("option", "", "Todos os canais"));
  select.firstElementChild.value = "todos";
  for (const c of state.snapshot.canais) {
    const opt = el("option", "", c.nome);
    opt.value = c.id;
    select.append(opt);
  }
  state.canal = state.snapshot.canais.some(c => c.id === previous) ? previous : "todos";
  select.value = state.canal;
}
function renderDashboard() {
  const snapshot = state.snapshot;
  const total = snapshot.agentes.length;
  const running = snapshot.agentes.filter(a => active(a.status)).length;
  $("countAgents").textContent = total;
  $("countActive").textContent = running;
  $("countChannels").textContent = snapshot.canais.length;
  $("countPending").textContent = snapshot.agentes.filter(a => a.status === "aguardando").length;
  const noEvents = snapshot.fonte !== "eventos_backend";
  $("sourceLabel").textContent = noEvents ? "Prévia · sem agentes ativos" : "Snapshot do backend";
  $("lastUpdate").textContent = "Atualizado: " + friendlyDate(snapshot.gerado_em);
  $("noticeText").textContent = noEvents
    ? "Este é um escritório de demonstração. Os oito agentes estão cadastrados, mas nenhum processo de IA foi conectado. O painel não executa tarefas."
    : "Os estados exibidos vieram de um relatório do backend. Esta é uma fotografia do último deploy, não uma transmissão em tempo real.";
  updateFilters();
  renderAgents();
  renderInspector();
  renderChannels();
}
async function load() {
  try {
    const response = await fetch("./data/status.json?v=" + Date.now(), { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (!data || data.schema !== "videoforge/agent-office/v1" || !Array.isArray(data.agentes) || !Array.isArray(data.canais)) {
      throw new Error("Dados do painel inválidos");
    }
    state.snapshot = data;
    renderDashboard();
  } catch (error) {
    if (!state.snapshot) {
      $("agentFloor").replaceChildren(el("p", "loading", "Não foi possível carregar o snapshot. Execute o exportador antes de abrir o site."));
      $("channelsList").replaceChildren(el("p", "loading", "Dados indisponíveis."));
      $("sourceLabel").textContent = "Snapshot indisponível";
    }
    $("lastUpdate").textContent = "Sem atualização";
    $("noticeText").textContent = "O painel não conseguiu acessar dados válidos. Nenhuma atividade foi presumida.";
    console.error("Falha ao carregar status:", error);
  }
}
$("channelFilter").addEventListener("change", (event) => {
  state.canal = event.target.value;
  if (state.snapshot) renderChannels();
});
$("footerYear").textContent = String(new Date().getFullYear());
load();
setInterval(load, 60000);
