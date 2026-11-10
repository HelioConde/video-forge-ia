/* Sequências de interação demonstrativas.
   Sem backend: movimentos apenas, sem alterar móveis, portas ou estados reais. */
(() => {
  "use strict";
  const step=(motion,ms,label)=>Object.freeze({motion,ms,label});
  const PLANS=Object.freeze({
    coffee:[
      step("open_door",420,"Chegada à copa (prévia)"),
      step("grab_mug",550,"Pegando caneca"),
      step("place_mug_machine",550,"Posicionando caneca"),
      step("make_coffee",850,"Preparando café"),
      step("pick_up_coffee",500,"Pegando café"),
      step("sip_coffee",1000,"Tomando café"),
      step("coffee_chat",600,"Pausa para conversar"),
      step("wash_mug",600,"Lavando caneca"),
      step("return_mug",470,"Guardando caneca")
    ],
    water:[
      step("grab_cup",550,"Pegando copo"),
      step("fill_water",1000,"Enchendo copo"),
      step("drink_water",1100,"Bebendo água"),
      step("refill_water",650,"Enchendo novamente"),
      step("discard_cup",600,"Descartando copo")
    ],
    games:[
      step("sit_on_sofa",750,"Sentando para jogar"),
      step("grab_controller",550,"Pegando controle"),
      step("play_gamepad",1200,"Jogando videogame"),
      step("game_focus",900,"Concentrado no jogo"),
      step("game_victory",700,"Comemorando vitória"),
      step("game_defeat",650,"Reagindo à partida"),
      step("watch_friend_play",750,"Assistindo à partida"),
      step("play_arcade",900,"Testando arcade (prévia)"),
      step("play_pool",800,"Jogo de sinuca (prévia)"),
      step("play_cards",750,"Jogo de cartas (prévia)"),
      step("play_boardgame",750,"Jogo de tabuleiro (prévia)"),
      step("leave_controller",530,"Devolvendo o controle")
    ],
    restroom:[
      step("open_restroom_door",700,"Entrada do banheiro (prévia)"),
      step("wash_hands",1200,"Lavando as mãos (prévia)"),
      step("dry_hands",850,"Secando as mãos (prévia)"),
      step("use_mirror",750,"Arrumando o cabelo (prévia)"),
      step("close_restroom_door",600,"Saindo do banheiro (prévia)")
    ],
    home:[
      step("pull_chair",650,"Puxando cadeira"),
      step("sit_down",650,"Sentando"),
      step("adjust_chair",600,"Ajustando postura"),
      step("lean_forward",500,"Conferindo monitor"),
      step("sit",1000,"Na estação de trabalho")
    ]
  });
  // Uma sequência não é um sprite único: usa percurso + passos disponíveis.
  // 'use_elevator' fica indisponível enquanto não existir elevador no cenário.
  const COMPOSITES=Object.freeze({
    approach_person:{destination:"meeting",availability:"demo"},
    goodbye:{destination:"meeting",availability:"demo"},
    approach_chair:{destination:"home",availability:"demo"},
    enter_breakroom:{destination:"coffee",availability:"demo"},
    approach_coffee_machine:{destination:"coffee",availability:"demo"},
    approach_water_cooler:{destination:"water",availability:"demo"},
    leave_water_cooler:{destination:"water",availability:"demo"},
    enter_game_room:{destination:"games",availability:"demo"},
    approach_restroom:{destination:"restroom",availability:"demo"},
    enter_restroom:{destination:"restroom",availability:"entrance_only"},
    exit_restroom:{destination:"restroom",availability:"entrance_only"},
    use_elevator:{destination:null,availability:"blocked_no_elevator"}
  });
  const ALL=Object.freeze(["coffee","water","games","restroom","home"]);
  function steps(target){return PLANS[target]||[];}
  function duration(target){return steps(target).reduce((total,s)=>total+s.ms,0);}
  function sample(target,elapsed){
    const entries=steps(target);
    let dt=Math.max(0,Number(elapsed)||0);
    for(const s of entries){
      if(dt<s.ms)return {...s,frame:Math.floor(dt/180)%4};
      dt-=s.ms;
    }
    return null;
  }
  function motions(target){
    return [...new Set(steps(target).map(s=>s.motion).filter(m=>m!=="sit"))];
  }
  window.VideoForgeInteractions={
    steps,duration,sample,motions,targets:ALL.slice(),composites:COMPOSITES
  };
})();