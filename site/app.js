/* VideoForge AI Pixel Office — interface e dados verificáveis, sem simular trabalhos. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const STATUS={nao_conectado:"Não conectado",aguardando:"Aguardando",trabalhando:"Trabalhando",revisao:"Em revisão",concluido:"Concluído",erro:"Erro"};
  const ICON={diretor:"◆",roteirista:"✎",artista:"✿",animador:"♜",narrador:"♫",editor:"▣",revisor:"✓",publicador:"↗"};
  const state={snapshot:null,selected:null,tab:"agents",open:false};
  const canvas=$("officeCanvas"), workspace=$("workspace");
  const office=new window.VideoForgeOffice.Office(canvas,id=>{state.selected=id;state.tab="agents";setOpen(true);render();});
  window.VideoForgeAnimator.preload().then(ready=>{
    office.setAgentSpritesReady(ready);
    if(state.snapshot)renderPanel();
  });
  state.previewMotion=null;
  const freeTimeButton=$("btnFreeTime");
  function syncFreeTimeButton(){
    const on=office.freeTimeDemoEnabled();
    freeTimeButton.setAttribute("aria-pressed",String(on));
    freeTimeButton.classList.toggle("active",on);
    freeTimeButton.title=on?"Desativar simulação visual de tempo livre":"Ativar simulação visual de tempo livre";
    freeTimeButton.setAttribute("aria-label",freeTimeButton.title);
  }
  freeTimeButton.disabled=true;
  freeTimeButton.addEventListener("click",()=>{
    office.setFreeTimeDemo(!office.freeTimeDemoEnabled());
    syncFreeTimeButton();
    if(state.snapshot)renderPanel();
  });
  const artBtn=$("btnArtMode");
  function updateArtButton(){
    const active=office.getArtMode()==='pixellab';
    artBtn.setAttribute('aria-pressed',String(active));
    artBtn.classList.toggle('active',active);
    artBtn.title=active?'Voltar ao cenário original':'Ativar cenários e objetos PixelLab';
    artBtn.setAttribute('aria-label',artBtn.title);
    artBtn.textContent=active?'▦':'✦';
  }
  artBtn.disabled=true;
  artBtn.title='Carregando sprites PixelLab';
  window.VideoForgeArt.loadSprites().then(ready=>{
    artBtn.disabled=!ready;
    if(ready)office.setArtMode('pixellab');
    freeTimeButton.disabled=!ready;
    syncFreeTimeButton();
    updateArtButton();
    if(state.snapshot)renderPanel();
  });
  artBtn.addEventListener('click',()=>{
    office.setArtMode(office.getArtMode()==='pixellab'?'classic':'pixellab');
    updateArtButton();
    freeTimeButton.disabled=office.getArtMode()!=='pixellab'||!window.VideoForgeAnimator.ready();
    syncFreeTimeButton();
    if(state.snapshot)renderPanel();
  });
  office.setMiniMap($("officeMiniMap"));
  const miniPanel=document.querySelector(".mini-panel");
  const miniToggle=$("btnMiniMap");
  miniToggle.addEventListener("click",()=>{
    const opening=miniPanel.dataset.collapsed==="true";
    miniPanel.dataset.collapsed=String(!opening);
    miniToggle.setAttribute("aria-expanded",String(opening));
  });
  const make=(tag,cls,text)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);return x;};
  const label=x=>STATUS[x]||"Indisponível";
  const live=x=>["trabalhando","revisao"].includes(x);
  const dot=x=>x==="erro"?"error":live(x)?"running":x==="aguardando"?"waiting":"";
  function setOpen(on){state.open=on;const panel=$("sidePanel");panel.classList.toggle("open",on);panel.setAttribute("aria-hidden",String(!on));$("btnAgents").setAttribute("aria-expanded",String(on&&state.tab==="agents"));$("btnChannels").setAttribute("aria-expanded",String(on&&state.tab==="channels"));}
  function selectTab(tab){state.tab=tab;setOpen(true);renderPanel();}
  function agentCard(a){const b=make("button","agent-item"+(state.selected===a.id?" active":""));b.type="button";b.setAttribute("aria-pressed",String(state.selected===a.id));const portrait=make("span","avatar-box",ICON[a.id]||"◇");portrait.setAttribute("aria-hidden","true");
    const body=make("span","agent-item-main");body.append(make("strong","",a.nome),make("small","",a.funcao));
    const status=make("i","state-dot "+dot(a.status));status.setAttribute("aria-label",label(a.status));b.append(portrait,body,status);
    b.addEventListener("click",()=>{
      state.selected=a.id;
      state.previewMotion=null;office.setPreviewMotion(null);
      office.setSelected(a.id);office.focusAgent(a.id);renderPanel();
    });
    return b;
  }
  function channelCard(c){const b=make("button","channel-item");b.type="button";
    const portrait=make("span","avatar-box","▶");portrait.setAttribute("aria-hidden","true");
    const body=make("span","channel-item-main");body.append(make("strong","",c.nome),make("small","",c.idioma+" · "+c.modelo));
    b.append(portrait,body);b.addEventListener("click",()=>{state.selectedChannel=c.id;renderPanel();});b.classList.toggle("active",state.selectedChannel===c.id);return b;
  }
  function renderPanel(){
    const snap=state.snapshot;if(!snap)return;
    const isAgents=state.tab==="agents";
    $("panelSection").textContent=isAgents?"01 / EQUIPE":"02 / CANAIS";
    $("panelTitle").textContent=isAgents?"Equipe do VideoForge":"Linhas de produção";
    $("tabAgents").classList.toggle("active",isAgents);$("tabChannels").classList.toggle("active",!isAgents);
    $("tabAgents").setAttribute("aria-selected",String(isAgents));$("tabChannels").setAttribute("aria-selected",String(!isAgents));
    const root=$("panelList"),frag=document.createDocumentFragment();
    (isAgents?snap.agentes:snap.canais).forEach(item=>frag.append(isAgents?agentCard(item):channelCard(item)));
    root.replaceChildren(frag);
    const detail=$("panelDetails");detail.replaceChildren();
    if(isAgents){const a=snap.agentes.find(a=>a.id===state.selected)||snap.agentes[0];if(!a)return;
      detail.append(make("div","detail-kicker","AGENTE SELECIONADO"),make("div","detail-title",a.nome),make("div","detail-status","● "+label(a.status)),make("p","detail-text",a.tarefa||"Nenhuma tarefa informada"));
      const channel=snap.canais.find(c=>c.id===a.canal);
      detail.append(make("div","detail-footnote","Canal: "+(channel?channel.nome:"Não atribuído")));
      if(window.VideoForgeAnimator.ready()){
        const preview=make("button","animation-preview");
        preview.type="button";
        const motions=[null,"idle","walk","type","sit","talk","wave"];
        preview.textContent=state.previewMotion?
          "Prévia do sprite: "+state.previewMotion+" · próximo":
          "Testar animações (prévia)";
        preview.setAttribute("aria-label","Alternar prévia das animações do Alex, sem alterar status real");
        preview.addEventListener("click",()=>{
          state.previewMotion=motions[(motions.indexOf(state.previewMotion)+1)%motions.length];
          office.setPreviewMotion(state.previewMotion);
          renderPanel();
        });
        detail.append(preview,make("small","preview-note",
          "Prévia visual. Não indica trabalho real do agente."));
      }
      if(window.VideoForgeAnimator.ready()&&office.getArtMode()==='pixellab'){
        const section=make("div","routine-section");
        section.append(make("div","routine-title","PASSEIOS NO ESCRITÓRIO · DEMONSTRAÇÃO"));
        section.append(make("small","preview-note",
          "Usa somente walk/idle. Beber, jogar e usar o banheiro ainda não têm animação própria."));
        const destination=[
          ["coffee","Ir ao café"],["water","Ir ao bebedouro"],
          ["games","Ir aos jogos (prévia)"],["restroom","Ir à porta do banheiro"],
          ["home","Voltar à mesa"]
        ];
        const buttons=make("div","routine-buttons");
        const canPreview=!live(a.status)&&a.status!=='erro';
        destination.forEach(([key,word])=>{
          const button=make("button","routine-button",word);
          button.type="button";
          button.dataset.destination=key;
          button.disabled=!canPreview;
          button.title=canPreview?"Rota ilustrativa, não execução real":"Indisponível durante atividade real";
          button.addEventListener("click",()=>{
            state.previewMotion=null;
            office.setPreviewMotion(null);
            if(office.travelSelected(key)){
              syncFreeTimeButton();
              const text=section.querySelector(".routine-state");
              if(text)text.textContent=office.routineState(a.id);
            }
          });
          buttons.append(button);
        });
        section.append(buttons);
        section.append(make("div","routine-state",office.routineState(a.id)));
        section.append(make("small","preview-note",
          office.freeTimeDemoEnabled()?
            "Tempo livre visual ativo: agentes disponíveis alternam passeios (não é trabalho real).":
            "Para passeios automáticos demonstrativos, ative ☕ na barra de ferramentas."));
        detail.append(section);
      }
    }else{const c=snap.canais.find(c=>c.id===state.selectedChannel)||snap.canais[0];if(!c)return;
      detail.append(make("div","detail-kicker","CANAL REGISTRADO"),make("div","detail-title",c.nome),make("div","detail-status",c.idioma+" · "+c.modelo),make("p","detail-text","O painel não publica vídeos. Este canal ainda não está conectado a um executor de IA."));
    }
  }
  function render(){
    const snap=state.snapshot;if(!snap)return;
    if(!snap.agentes.find(a=>a.id===state.selected))state.selected=snap.agentes[0]?.id||null;
    office.setAgents(snap.agentes);office.setSelected(state.selected);
    $("agentsCount").textContent=String(snap.agentes.length);
    $("activeCount").textContent=String(snap.agentes.filter(a=>live(a.status)).length);
    $("channelsCount").textContent=String(snap.canais.length);
    const actual=snap.fonte==="eventos_backend";
    $("sceneSource").textContent=actual?"SNAPSHOT DE ATIVIDADE":"SEM EXECUÇÃO DE AGENTES";
    $("connectionBadge").dataset.live=String(actual);
    $("connectionBadge").lastChild.textContent=actual?" SNAPSHOT RECEBIDO":" NÃO CONECTADO";
    if(snap.gerado_em){const d=new Date(snap.gerado_em);$("snapshotAge").textContent=isNaN(d.getTime())?"Sem data":"Snapshot "+d.toLocaleString("pt-BR",{dateStyle:"short",timeStyle:"short"});}
    renderPanel();
  }
  async function load(){
    try{
      const response=await fetch("./data/status.json?t="+Date.now(),{cache:"no-store"});
      if(!response.ok)throw new Error("HTTP "+response.status);
      const data=await response.json();
      if(!data||data.schema!=="videoforge/agent-office/v1"||!Array.isArray(data.agentes)||!Array.isArray(data.canais))throw new Error("Formato de snapshot inválido");
      state.snapshot=data;render();
    }catch(err){
      $("sceneSource").textContent="SNAPSHOT INDISPONÍVEL";
      $("snapshotAge").textContent="Sem dados";
      console.error("VideoForge: erro no snapshot",err);
    }
  }
  $("btnZoomIn").addEventListener("click",()=>office.zoomAt(1.2));
  $("btnZoomOut").addEventListener("click",()=>office.zoomAt(1/1.2));
  $("btnReset").addEventListener("click",()=>office.reset());
  $("btnFullscreen").addEventListener("click",async()=>{
    try{if(document.fullscreenElement){await document.exitFullscreen();}else if(workspace.requestFullscreen){await workspace.requestFullscreen();}}
    catch(err){console.warn("Modo tela cheia não disponível:",err);}
  });
  $("btnAgents").addEventListener("click",()=>{if(state.open&&state.tab==="agents"){setOpen(false);}else selectTab("agents");});
  $("btnChannels").addEventListener("click",()=>{if(state.open&&state.tab==="channels"){setOpen(false);}else selectTab("channels");});
  $("btnClose").addEventListener("click",()=>setOpen(false));
  $("tabAgents").addEventListener("click",()=>selectTab("agents"));
  $("tabChannels").addEventListener("click",()=>selectTab("channels"));
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"&&state.open)setOpen(false);
    if((e.key==="+"||e.key==="=")&&!(e.target instanceof HTMLInputElement))office.zoomAt(1.15);
    if(e.key==="-"&&!(e.target instanceof HTMLInputElement))office.zoomAt(1/1.15);
  });
  load();window.setInterval(load,60000);
})();