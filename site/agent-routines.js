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
    function clear() {state.clear();}
    function cancel(id) {state.delete(id);}
    function current(id,now=0) {
      const pose=poseFor(id,now);
      if(!pose)return "Na mesa (sem demonstração)";
      return pose.moving?"Caminhando para: "+pose.label:
             "No destino: "+pose.label+" · ação específica ainda não animada";
    }
    return {travel,poseFor,clear,cancel,current,
            destinations:Object.keys(DESTINATIONS),
            definitions:DESTINATIONS,
            heading};
  }
  window.VideoForgeRoutines={create,heading,definitions:DESTINATIONS};
})();
