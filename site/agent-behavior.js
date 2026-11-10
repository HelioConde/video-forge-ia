/* Movimentos específicos por função — estado real sempre vem do backend.
   Simulação de trabalho/convivência é opt-in e nunca cria eventos de execução. */
(() => {
  "use strict";
  const PROFILES=Object.freeze({
    diretor:{label:"Direção",work:["talk_explain","presentation","team_meeting","listen_focus"],demo:["presentation","talk_explain","listen_focus","think_response"],fallback:"talk"},
    roteirista:{label:"Roteirista",work:["keyboard_type","read_document","inspect_script","write_notes"],demo:["read_document","keyboard_type","think_response","write_notes"],fallback:"type"},
    artista:{label:"Artista visual",work:["draw_tablet","draw_layers","inspect_art","point_at_storyboard"],demo:["draw_tablet","inspect_art","draw_layers","think_response"],fallback:"type"},
    animador:{label:"Animador",work:["animation_review","review_storyboard","mouse_move","point_at_storyboard"],demo:["animation_review","review_storyboard","mouse_move","listen_focus"],fallback:"type"},
    narrador:{label:"Narrador",work:["narrate","listen_recording","adjust_microphone","sing_seated"],demo:["narrate","listen_recording","sing_seated","adjust_microphone"],fallback:"talk"},
    editor:{label:"Editor",work:["edit_video","subtitle_edit","keyboard_shortcuts","mouse_click"],demo:["edit_video","subtitle_edit","keyboard_shortcuts","listen_focus"],fallback:"type"},
    revisor:{label:"Revisor",work:["qa_inspection","read_document","inspect_script","think_response"],demo:["qa_inspection","read_document","think_response","listen_focus"],fallback:"talk"},
    publicador:{label:"Publicador",work:["keyboard_shortcuts","mouse_click","qa_inspection","keyboard_type"],demo:["keyboard_shortcuts","mouse_click","qa_inspection","talk_serious"],fallback:"type"}
  });
  const ORDER=Object.keys(PROFILES);
  // Cada especialidade expõe sua galeria, sem executar IA nem simular tarefas reais.
  const ROLE_CATEGORIES=Object.freeze({
    diretor:["conversa","emocoes","cadeira","descanso","ambiente"],
    roteirista:["trabalho","conversa","cadeira","descanso","cafe"],
    artista:["trabalho","conversa","cafe","agua","emocoes"],
    animador:["trabalho","jogos","conversa","descanso","cadeira"],
    narrador:["trabalho","conversa","cafe","agua","banheiro"],
    editor:["trabalho","jogos","cadeira","emocoes","ambiente"],
    revisor:["trabalho","conversa","banheiro","agua","descanso"],
    publicador:["ambiente","jogos","trabalho","cafe","emocoes","banheiro"]
  });
  const STATION_DEMO=new Set(["emocoes","descanso"]);
  const ACTIVE=new Set(["trabalhando","revisao"]);
  function profile(id){return PROFILES[id]||null;}
  function choose(agent, now, demoEnabled, ready, catalog=[]){
    if(!agent||!profile(agent.id))return "idle";
    if(agent.status==="erro")return "idle";
    const item=profile(agent.id);
    const running=ACTIVE.has(agent.status);
    if(!running&&!demoEnabled)return agent.status==="concluido"?"wave":"idle";
    // Emoções e descanso aparecem apenas na demonstração opt-in.
    // Café, banheiro e jogos só ocorrem em rotas contextuais, não no posto.
    const extra=!running&&demoEnabled?catalog.filter(x=>
      ROLE_CATEGORIES[agent.id]?.includes(x.category) &&
      STATION_DEMO.has(x.category)).map(x=>x.name):[];
    const options=[...new Set([...(running?item.work:item.demo),...extra])]
      .filter(x=>ready(x));
    if(!options.length)return running?item.fallback:"idle";
    const index=(Math.floor(Math.max(0,now)/3600)+ORDER.indexOf(agent.id))%options.length;
    return options[index];
  }
  async function preload(animator){
    if(!animator||typeof animator.preloadProduction!=="function")return [];
    await animator.loadProductionManifest();
    const available=new Set(animator.productionMotions().map(x=>x.name));
    const sprites=[...new Set(Object.values(PROFILES).flatMap(p=>[...p.work,...p.demo]))]
      .filter(m=>available.has(m));
    const results=await Promise.all(sprites.map(async name=>({name,ok:await animator.preloadProduction(name)})));
    return results.filter(x=>x.ok).map(x=>x.name);
  }
  function names(id,catalog=[]){
    const item=profile(id);
    return item?[...new Set([...item.work,...item.demo,...catalog
      .filter(x=>ROLE_CATEGORIES[id]?.includes(x.category)).map(x=>x.name)])]:[];
  }
  function categories(id){return ROLE_CATEGORIES[id]?.slice()||[];}
  window.VideoForgeBehaviors={profile,names,choose,preload,categories,roles:ORDER.slice()};
})();