"use strict";
// Testa o comportamento do escritório usando somente mocks do Canvas,
// sem consultas à API, vídeo ou geração paga PixelLab.
const assert=require("node:assert/strict");
global.window={};
require("../site/office-map.js");
const map=window.VideoForgeOfficeMap;
const draws=[];
global.Image=class {
  constructor(){this.naturalWidth=96;this.naturalHeight=96;}
  set src(value){this._src=value;queueMicrotask(()=>this.onload?.());}
};
window.VideoForgeAnimator={
  ready:()=>true,
  productionMotions:()=>[],
  frameCount:name=>name==="walk"?8:4,
  drawProduction:()=>false,
  draw:(c,motion,direction,frame,x,y,size)=>{
    draws.push({motion,direction,frame,x,y,size});
    return ["idle","sit","walk","wave","talk","type"].includes(motion);
  }
};
window.VideoForgeBehaviors={choose:()=> "idle"};
require("../site/office-art.js");
const art=window.VideoForgeArt;
const canvas={
  fillRect(){},strokeRect(){},fillText(){},beginPath(){},ellipse(){},
  fill(){},save(){},restore(){},translate(){},scale(){},drawImage(){}
};
const agents=map.stations.map((p,i)=>({
  id:p.id,nome:"Agente "+i,status:"nao_conectado"
}));
function paint({selected=null,previewMotion=null,routines=null,roleDemo=false,agentsList=agents}={}){
  draws.length=0;
  art.paintAgents(canvas,agentsList,selected,1000,previewMotion,false,routines,roleDemo);
  return draws.slice();
}
(async()=>{
  assert.equal(await art.loadSprites(),true);
  assert.equal(art.setArtMode("pixellab"),true);
  assert.equal(art.slots.length,8);

  // Nenhum agente deve continuar em pé ao carregar o escritório.
  const seated=paint();
  assert.equal(seated.length,8);
  seated.forEach((actual,i)=>{
    const station=map.stations[i];
    assert.equal(actual.motion,"sit","Agente não ficou sentado: "+station.id);
    assert.equal(actual.direction,map.seat.direction);
    assert.equal(actual.frame,3,"Não repetir animação de levantar e sentar");
    assert.equal(actual.x,station.x+map.seat.dx);
    assert.equal(actual.y,station.y+111+map.seat.dy);
  });
  // Status de backend não muda a postura de quem está à mesa.
  agents[0].status="trabalhando";
  agents[1].status="revisao";
  assert.equal(paint()[0].motion,"sit");
  assert.equal(paint()[1].motion,"sit");
  agents[0].status="nao_conectado";
  agents[1].status="nao_conectado";

  // A caminhada mantém coordenadas, direção e frame; não senta no corredor.
  const walking={moving:true,target:"coffee",motion:"walk",direction:"west",
                 frame:6,x:600,y:460};
  let rendered=paint({agentsList:[agents[0]],routines:{poseFor:id=>id==="diretor"?walking:null}});
  assert.deepEqual(rendered[0],{motion:"walk",direction:"west",frame:6,x:600,y:460,size:72});

  // A pausa no café é em pé, não sentado na cadeira do escritório.
  rendered=paint({agentsList:[agents[0]],routines:{poseFor:id=>id==="diretor"?{
    moving:false,target:"coffee",motion:"idle",direction:"south",
    frame:0,x:857,y:572
  }:null}});
  assert.equal(rendered[0].motion,"idle");
  assert.equal(rendered[0].y,572);

  // Voltando para casa, o sprite encaixa de novo na cadeira.
  const station=map.stations[0];
  rendered=paint({agentsList:[agents[0]],routines:{poseFor:id=>id==="diretor"?{
    moving:false,target:"home",motion:"sit",direction:"south",frame:0,
    x:station.x,y:station.y+111
  }:null}});
  assert.equal(rendered[0].motion,"sit");
  assert.equal(rendered[0].direction,"north");
  assert.equal(rendered[0].frame,3);
  assert.equal(rendered[0].y,station.y+121);

  // A prévia manual de outra animação não deve ser bloqueada.
  rendered=paint({selected:"diretor",previewMotion:"wave",agentsList:[agents[0]]});
  assert.equal(rendered[0].motion,"wave");
  assert.equal(rendered[0].y,station.y+111);

  console.log("AGENT_SEATING_OK: 8 sentados, walk preservado, pausa e retorno corretos");
})().catch(error=>{console.error(error);process.exitCode=1;});
