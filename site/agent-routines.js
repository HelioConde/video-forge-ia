/* VideoForge AI — passeios interativos demonstrativos com sprites já existentes.
   Nenhum trajeto altera o status real de produção e não simula ações inexistentes. */
(() => {
  "use strict";

  const DESTINATIONS = Object.freeze({
    coffee: { x:704, y:614, label:"Ponto do café" },
    water: { x:893, y:607, label:"Bebedouro (marcação)" },
    games: { x:1148, y:696, label:"Jogos (área experimental)" },
    restroom: { x:1183, y:573, label:"Entrada do banheiro (marcação)" }
  });
  const HEADINGS = ["east","south-east","south","south-west",
                    "west","north-west","north","north-east"];
  const SPEED = 160; // pixels por segundo; orientação em oito direções.

  function heading(dx,dy) {
    if (Math.abs(dx)+Math.abs(dy) < 0.01) return "south";
    const step=Math.round(Math.atan2(dy,dx)/(Math.PI/4));
    return HEADINGS[(step%8+8)%8];
  }
  function cleanPoints(points) {
    return points.filter((p,i)=>i===0||Math.hypot(p.x-points[i-1].x,p.y-points[i-1].y)>1);
  }
  function travelRoute(from,to,home=false) {
    // Corredor visual inferior para transitar entre área de trabalho e anexos.
    // Não é pathfinding físico — só há interações nos pontos sinalizados.
    const corridorY=724;
    const points=[
      {x:from.x,y:from.y},
      {x:from.x,y:corridorY},
      {x:615,y:corridorY},
      {x:to.x,y:corridorY},
      {x:to.x,y:to.y}
    ];
    return cleanPoints(points);
  }
  function interpolate(points,distance) {
    for(let i=1;i<points.length;i++) {
      const prev=points[i-1],next=points[i];
      const len=Math.hypot(next.x-prev.x,next.y-prev.y);
      if(distance<=len) {
        const t=len?distance/len:1;
        return {x:prev.x+(next.x-prev.x)*t,y:prev.y+(next.y-prev.y)*t,
                direction:heading(next.x-prev.x,next.y-prev.y),moving:true};
      }
      distance-=len;
    }
    const last=points.at(-1);
    return {x:last.x,y:last.y,direction:"south",moving:false};
  }
  function create(slots) {
    const state=new Map();
    const freeTime={enabled:false,nextAt:0,agentId:null,phase:"idle",returnAt:0,index:0};
    const leisurePlaces=["coffee","water","games","restroom"];
    const knownIds=new Set([
      "diretor","roteirista","artista","animador","narrador","editor","revisor","publicador"
    ]);
    function home(id) {
      const names=[...knownIds],i=names.indexOf(id);
      if(i<0||!slots[i])return null;
      return {x:slots[i][0],y:slots[i][1]+111};
    }
    function poseFor(id, now=0) {
      const route=state.get(id);
      if(!route)return null;
      const elapsed=Math.max(0,(now-route.start)/1000)*SPEED;
      const position=interpolate(route.points,elapsed);
      return {...position, motion:position.moving?"walk":"idle",
              target:route.target, label:route.label, demo:true};
    }
    function travel(id,destination,now=0) {
      if(!knownIds.has(id)||!(destination==="home"||DESTINATIONS[destination]))return false;
      const origin=home(id);
      if(!origin)return false;
      const previous=poseFor(id,now);
      const start=previous?{x:previous.x,y:previous.y}:origin;
      const target=destination==="home"?origin:DESTINATIONS[destination];
      if(destination==="home"&&!previous)return true;
      state.set(id,{
        start:now,
        target:destination,
        label:destination==="home"?"Mesa de trabalho":target.label,
        points:travelRoute(start,target,destination==="home")
      });
      return true;
    }
    function setFreeTimeDemo(enabled,now=0){
      freeTime.enabled=Boolean(enabled);
      freeTime.nextAt=now+1200;
      if(!freeTime.enabled&&freeTime.agentId)state.delete(freeTime.agentId);
      freeTime.agentId=null;
      freeTime.phase="idle";
      return freeTime.enabled;
    }
    function tick(agents,now=0){
      if(!freeTime.enabled)return;
      if(freeTime.agentId){
        const id=freeTime.agentId;
        const agent=agents.find(a=>a.id===id);
        if(!agent||["trabalhando","revisao","erro"].includes(agent.status)){
          state.delete(id);
          freeTime.agentId=null;
          freeTime.phase="idle";
          freeTime.nextAt=now+5000;
          return;
        }
        const pose=poseFor(id,now);
        if(freeTime.phase==="outbound"&&pose&&!pose.moving){
          freeTime.phase="rest";
          freeTime.returnAt=now+6500;
        }else if(freeTime.phase==="rest"&&now>=freeTime.returnAt){
          travel(id,"home",now);
          freeTime.phase="returning";
        }else if(freeTime.phase==="returning"&&pose&&!pose.moving){
          state.delete(id);
          freeTime.agentId=null;
          freeTime.phase="idle";
          freeTime.nextAt=now+5500;
        }
        return;
      }
      if(now<freeTime.nextAt)return;
      const available=agents.filter(a=>[
        "nao_conectado","aguardando","concluido"
      ].includes(a.status)&&knownIds.has(a.id)&&!state.has(a.id));
      if(!available.length){freeTime.nextAt=now+6500;return;}
      const candidate=available[freeTime.index%available.length];
      const destination=leisurePlaces[freeTime.index%leisurePlaces.length];
      freeTime.index++;
      if(travel(candidate.id,destination,now)){
        freeTime.agentId=candidate.id;
        freeTime.phase="outbound";
      }
    }
    function clear() {
      state.clear();freeTime.enabled=false;freeTime.agentId=null;
      freeTime.phase="idle";
    }
    function cancel(id) {
      state.delete(id);
      if(freeTime.agentId===id) {
        freeTime.agentId=null;freeTime.phase="idle";
        freeTime.nextAt+=5000;
      }
    }
    function current(id,now=0) {
      const pose=poseFor(id,now);
      if(!pose)return "Na mesa (sem demonstração)";
      return pose.moving?"Caminhando para: "+pose.label:
             "No destino: "+pose.label+" · ação específica ainda não animada";
    }
    return {travel,poseFor,clear,cancel,current,tick,setFreeTimeDemo,
            freeTimeEnabled:()=>freeTime.enabled,
            destinations:Object.keys(DESTINATIONS),
            definitions:DESTINATIONS,
            heading};
  }
  window.VideoForgeRoutines={create,heading,definitions:DESTINATIONS};
})();
