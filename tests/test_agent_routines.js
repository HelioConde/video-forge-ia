/* Testes reais da lógica de trajetos, sem navegador nem API. */
"use strict";
const assert=require("node:assert/strict");
global.window={};
require("../site/agent-routines.js");
const mod=window.VideoForgeRoutines;
assert.equal(mod.heading(20,0),"east");
assert.equal(mod.heading(0,20),"south");
assert.equal(mod.heading(-20,0),"west");
assert.equal(mod.heading(0,-20),"north");
assert.equal(mod.heading(20,-20),"north-east");
const slots=[[205,143],[456,143],[205,253],[456,253],[205,363],[456,363],[205,473],[456,473]];
const sim=mod.create(slots);
assert.equal(sim.travel("diretor","coffee",1000),true);
const p0=sim.poseFor("diretor",1000);
assert.equal(p0.x,205);
assert.equal(p0.y,254);
assert.equal(p0.motion,"walk");
const p1=sim.poseFor("diretor",2000);
assert.equal(p1.motion,"walk");
assert(p1.y>254,"caminha em direção ao corredor");
const p2=sim.poseFor("diretor",12000);
assert.equal(p2.motion,"idle");
assert.equal(Math.round(p2.x),704);
assert.equal(Math.round(p2.y),614);
assert.equal(sim.travel("diretor","home",12000),true);
const p3=sim.poseFor("diretor",23000);
assert.equal(p3.motion,"idle");
assert.equal(Math.round(p3.x),205);
assert.equal(Math.round(p3.y),254);
assert.equal(sim.travel("inexistente","coffee",1),false);
assert.equal(sim.travel("diretor","secret",1),false);
sim.clear();
assert.equal(sim.poseFor("diretor",24000),null);
const auto=mod.create(slots);
const agents=[{id:"diretor",status:"nao_conectado"}];
assert.equal(auto.setFreeTimeDemo(true,0),true);
auto.tick(agents,1100);
assert.equal(auto.poseFor("diretor",1100),null);
auto.tick(agents,1500);
assert.equal(auto.poseFor("diretor",1500).target,"coffee");
auto.tick(agents,16000);
assert.equal(auto.poseFor("diretor",16000).motion,"idle");
auto.tick(agents,23000);
assert.equal(auto.poseFor("diretor",23000).target,"home");
auto.tick(agents,35000);
assert.equal(auto.poseFor("diretor",35000),null);
auto.setFreeTimeDemo(false,35000);
assert.equal(auto.freeTimeEnabled(),false);
auto.tick(agents,40000);
assert.equal(auto.poseFor("diretor",40000),null);
const work=mod.create(slots);
work.setFreeTimeDemo(true,0);
work.tick([{id:"diretor",status:"trabalhando"}],2000);
assert.equal(work.poseFor("diretor",2000),null);
console.log("ROTINAS_PREVIA_OK: caminhada, tempo livre opt-in e prioridade ao backend");

const meeting=mod.create(slots);
assert.equal(meeting.meet("diretor","roteirista",1000),true);
assert.equal(meeting.meet("diretor","roteirista",1002),false);
const first=meeting.poseFor("diretor",1000);
const second=meeting.poseFor("roteirista",1000);
assert.equal(first.motion,"walk");
assert.notEqual(first.x,second.x);
const speakerTime=14000;
meeting.tick([
  {id:"diretor",status:"nao_conectado"},
  {id:"roteirista",status:"nao_conectado"}
],speakerTime);
const one=meeting.poseFor("diretor",speakerTime);
const two=meeting.poseFor("roteirista",speakerTime);
assert.equal([one.motion,two.motion].filter(x=>x==="talk_explain").length,1);
assert.equal([one.motion,two.motion].filter(x=>x==="listen_focus").length,1);
assert(one.x!==two.x,"personagens não ocupam o mesmo ponto de reunião");
assert(meeting.current("diretor",speakerTime).includes("Conversa"));
meeting.tick([
  {id:"diretor",status:"nao_conectado"},
  {id:"roteirista",status:"nao_conectado"}
],60000);
assert.equal(meeting.poseFor("diretor",60000).target,"home");
const interrupted=mod.create(slots);
assert.equal(interrupted.meet("diretor","roteirista",1000),true);
interrupted.tick([
  {id:"diretor",status:"trabalhando"},
  {id:"roteirista",status:"nao_conectado"}
],1100);
assert.equal(interrupted.poseFor("diretor",1100),null);
assert.equal(interrupted.poseFor("roteirista",1100),null);
console.log("CONVERSAS_PREVIA_OK: deslocamento, alternância e cancelamento por atividade real");

const smooth=mod.create(slots);
assert.equal(smooth.travel("diretor","water",1000),true);
assert.equal(smooth.hasMoving(1000),true);
const initial=smooth.poseFor("diretor",1000);
assert.equal(initial.frame,0);
assert.equal(initial.motion,"walk");
// Caminhada em 30 FPS deve percorrer menos de 4 pixels de mundo por quadro.
for(let t=1000;t<=2400;t+=33){
  const a=smooth.poseFor("diretor",t);
  const b=smooth.poseFor("diretor",t+33);
  assert(Math.hypot(b.x-a.x,b.y-a.y)<=4.1,
    "walk precisa manter deslocamento contínuo em cada frame");
}
assert.notEqual(smooth.poseFor("diretor",1600).frame,initial.frame,
  "a passada deve evoluir conforme a distância percorrida");
const directions=new Set();
for(let t=1000;t<15000;t+=40){
  const pose=smooth.poseFor("diretor",t);
  if(pose.moving)directions.add(pose.direction);
}
assert([...directions].some(x=>x.includes("-")),
  "a curva do corredor precisa passar por direção diagonal");
assert.equal(smooth.poseFor("diretor",100000).motion,"idle");
assert.equal(smooth.hasMoving(100000),false);
smooth.travel("diretor","coffee",123456);
assert.equal(smooth.poseFor("diretor",123456).frame,0,
  "novo trajeto não pode herdar a fase do relógio global");
console.log("WALK_SMOOTH_OK: posição contínua, curva diagonal e passada por distância");
