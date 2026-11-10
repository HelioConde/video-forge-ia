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
  const SPEED = 112; // px/seg; a 30 FPS são aproximadamente 3,7 px por desenho.
  const WALK_CYCLE_DISTANCE = 56; // ciclo completo em pixels, seja 4 ou 8 frames.
  const TURN_RADIUS = 18; // curva curta entre mudanças de direção.

  function heading(dx,dy) {
    if (Math.abs(dx)+Math.abs(dy) < 0.01) return "south";
    const step=Math.round(Math.atan2(dy,dx)/(Math.PI/4));
    return HEADINGS[(step%8+8)%8];
  }
  function cleanPoints(points) {
    return points.filter((p,i)=>i===0||Math.hypot(p.x-points[i-1].x,p.y-points[i-1].y)>1);
  }
  function softenCorners(points) {
    const input=cleanPoints(points),result=[input[0]];
    if(input.length<3)return input;
    for(let i=1;i<input.length-1;i++){
      const a=input[i-1],b=input[i],c=input[i+1];
      const dx1=b.x-a.x,dy1=b.y-a.y,dx2=c.x-b.x,dy2=c.y-b.y;
      const len1=Math.hypot(dx1,dy1),len2=Math.hypot(dx2,dy2);
      if(len1<1||len2<1){result.push(b);continue;}
      const ix=dx1/len1,iy=dy1/len1,ox=dx2/len2,oy=dy2/len2;
      if(Math.abs(ix*oy-iy*ox)<0.03){result.push(b);continue;}
      const radius=Math.min(TURN_RADIUS,len1*.3,len2*.3);
      if(radius<2){result.push(b);continue;}
      const p={x:b.x-ix*radius,y:b.y-iy*radius};
      const q={x:b.x+ox*radius,y:b.y+oy*radius};
      result.push(p);
      for(const t of [.25,.5,.75]){
        const u=1-t;
        result.push({x:u*u*p.x+2*u*t*b.x+t*t*q.x,
                     y:u*u*p.y+2*u*t*b.y+t*t*q.y});
      }
      result.push(q);
    }
    result.push(input.at(-1));
    return cleanPoints(result);
  }
  function travelRoute(from,to,home=false) {
    // Acesso pelo corredor central entre as mesas, sem atravessar os
    // outros agentes nas cadeiras. Rotas permanecem demonstrativas.
    const corridorY=724,aisleX=328,doorX=615;
    const points=home?[
      {x:from.x,y:from.y},
      {x:from.x,y:corridorY},
      {x:doorX,y:corridorY},
      {x:aisleX,y:corridorY},
      {x:aisleX,y:to.y},
      {x:to.x,y:to.y}
    ]:[
      {x:from.x,y:from.y},
      {x:aisleX,y:from.y},
      {x:aisleX,y:corridorY},
      {x:doorX,y:corridorY},
      {x:to.x,y:corridorY},
      {x:to.x,y:to.y}
    ];
    return softenCorners(points);
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
    const prev=points.at(-2)||last;
    return {x:last.x,y:last.y,direction:heading(last.x-prev.x,last.y-prev.y),moving:false};
  }
  function create(slots) {
    const state=new Map();
    let meeting=null; // demonstração sincronizada de dois agents, sem backend
    const freeTime={enabled:false,nextAt:0,agentId:null,phase:"idle",returnAt:0,index:0};
    const leisurePlaces=["coffee","water","games","restroom"];
    const choreography=window.VideoForgeInteractions;
    const knownIds=new Set([
      "diretor","roteirista","artista","animador","narrador","editor","revisor","publicador"
    ]);
    function home(id) {
      const names=[...knownIds],i=names.indexOf(id);
      if(i<0||!slots[i])return null;
      return {x:slots[i][0],y:slots[i][1]+111};
    }
    function routeDistance(points){
      return points.slice(1).reduce((total,p,i)=>
        total+Math.hypot(p.x-points[i].x,p.y-points[i].y),0);
    }
    function poseFor(id, now=0) {
      const route=state.get(id);
      if(!route)return null;
      const distance=Math.min(route.distance,Math.max(0,(now-route.start)/1000)*SPEED);
      const position=interpolate(route.points,distance);
      position.moving=distance<route.distance-0.01;
      if(!position.moving){
        const last=route.points.at(-1),before=route.points.at(-2)||last;
        position.direction=heading(last.x-before.x,last.y-before.y);
      }
      const frameCount=window.VideoForgeAnimator?.frameCount?.("walk")===8?8:4;
      const walkStride=WALK_CYCLE_DISTANCE/frameCount;
      const walkFrame=position.moving?Math.floor(distance/walkStride)%frameCount:0;
      let motion=position.moving?"walk":"idle";
      let direction=position.direction;
      let actionLabel=null;
      let frame=walkFrame;
      if(!position.moving&&choreography&&route.target!=="meeting"){
        const arrival=route.start+route.distance/SPEED*1000;
        const step=choreography.sample(route.target,now-arrival);
        if(step){
          motion=step.motion;
          frame=step.frame;
          actionLabel=step.label+" · simulação visual";
        }else if(route.target==="home"){
          motion="sit";
        }
      }
      if(!position.moving&&meeting&&(id===meeting.a||id===meeting.b)){
        if(now>=meeting.begin&&now<meeting.end){
          const turn=Math.floor((now-meeting.begin)/3000)%2;
          const talking=(turn===0?meeting.a:meeting.b)===id;
          motion=talking?"talk_explain":"listen_focus";
          frame=Math.floor((now-meeting.begin)/180)%4;
          direction=id===meeting.a?"east":"west";
          actionLabel=talking?"Explicando a tarefa (prévia)":"Ouvindo o colega (prévia)";
        }else if(now>=meeting.end){
          motion="wave";
          frame=Math.floor((now-meeting.end)/180)%4;
          actionLabel="Despedida (prévia)";
        }
      }
      return {...position,direction,motion,frame,distance,
              target:route.target,label:route.label,actionLabel,demo:true};
    }
    function meet(a,b,now=0){
      if(a===b||!knownIds.has(a)||!knownIds.has(b)||meeting||state.has(a)||state.has(b))return false;
      // Mesas de reunião distintas: dois sprites nunca ocupam o mesmo ponto.
      const destinations=[{x:729,y:369},{x:834,y:369}];
      const pairs=[[a,destinations[0]],[b,destinations[1]]];
      const routes=pairs.map(([id,to])=>{
        const from=home(id);
        if(!from)return null;
        const points=travelRoute(from,to);
        return {id,points,to};
      });
      if(routes.some(x=>!x))return false;
      const travelMs=Math.max(...routes.map(x=>routeDistance(x.points)/SPEED*1000));
      const begin=now+travelMs+300;
      meeting={a,b,begin,end:begin+12000};
      routes.forEach(({id,points})=>{
        state.set(id,{start:now,target:"meeting",label:"Conversa na sala criativa (prévia)",
                      points,distance:routeDistance(points)});
      });
      if(freeTime.enabled)setFreeTimeDemo(false,now);
      return true;
    }
    function travel(id,destination,now=0) {
      if(!knownIds.has(id)||!(destination==="home"||DESTINATIONS[destination]))return false;
      if(meeting&&(id===meeting.a||id===meeting.b))cancel(id);
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
      state.get(id).distance=routeDistance(state.get(id).points);
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
      if(meeting){
        const a=agents.find(x=>x.id===meeting.a),b=agents.find(x=>x.id===meeting.b);
        if(!a||!b||[a,b].some(x=>["trabalhando","revisao","erro"].includes(x.status))){
          cancel(meeting.a);
        }else if(now>=meeting.end){
          const first=meeting.a,second=meeting.b;
          meeting=null;
          travel(first,"home",now);
          travel(second,"home",now);
        }
      }
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
          const dest=state.get(id)?.target;
          freeTime.returnAt=now+Math.max(6500,(choreography?.duration(dest)||0)+500);
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
    function hasMoving(now=0){
      for(const id of state.keys())if(poseFor(id,now)?.moving)return true;
      return false;
    }
    function clear() {
      state.clear();meeting=null;freeTime.enabled=false;freeTime.agentId=null;
      freeTime.phase="idle";
    }
    function cancel(id) {
      if(meeting&&(id===meeting.a||id===meeting.b)){
        state.delete(meeting.a);
        state.delete(meeting.b);
        meeting=null;
      }
      state.delete(id);
      if(freeTime.agentId===id) {
        freeTime.agentId=null;freeTime.phase="idle";
        freeTime.nextAt+=5000;
      }
    }
    function current(id,now=0) {
      const pose=poseFor(id,now);
      if(!pose)return "Na mesa (sem demonstração)";
      if(meeting&&(id===meeting.a||id===meeting.b))
        return pose.moving?"Indo à sala criativa (prévia)":"Conversa e escuta alternadas (prévia)";
      return pose.moving?"Caminhando para: "+pose.label:
             pose.actionLabel||("No destino: "+pose.label+" · demonstração visual");
    }
    return {travel,meet,poseFor,hasMoving,clear,cancel,current,tick,setFreeTimeDemo,
            freeTimeEnabled:()=>freeTime.enabled,
            destinations:Object.keys(DESTINATIONS),
            definitions:DESTINATIONS,
            heading};
  }
  window.VideoForgeRoutines={create,heading,definitions:DESTINATIONS};
})();
