"use strict";
// Testa o comportamento do escritório usando somente mocks do Canvas,
// sem consultas à API, vídeo ou geração paga PixelLab.
const assert=require("node:assert/strict");
global.window={};
require("../site/office-map.js");
const map=window.VideoForgeOfficeMap;
const draws=[];
const seatedCrops=[];
let animatorReady=true;
global.Image=class {
  constructor(){this.naturalWidth=96;this.naturalHeight=96;}
  set src(value){this._src=value;queueMicrotask(()=>this.onload?.());}
};
window.VideoForgeAnimator={
  ready:()=>animatorReady,
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
  fill(){},save(){},restore(){},translate(){},scale(){},
  drawImage(image,sx,sy,sw,sh,dx,dy,dw,dh){
    if(!String(image?._src).endsWith("/sit_down.png"))return;
    seatedCrops.push({sx,sy,sw,sh,dx,dy,dw,dh});
    // Normalizar o recorte PixelLab para comparar com movimentos do animator.
    // O quadro é cortado só embaixo; o centro lógico ainda é o do
    // sprite 88×88, não o centro do recorte parcial.
    draws.push({motion:"sit",direction:"north",frame:3,
                x:dx+dw/2,y:dy+dw/2,size:dw});
  }
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
  assert.equal(art.slots.length,9);
  assert.equal(map.seat.dy,0,"A cadeira da animação não deve projetar para o corredor");
  assert.equal(map.character.labelOffset,60,"Nome deve acompanhar o encaixe da cadeira");

  // Nenhum agente deve continuar em pé ao carregar o escritório.
  const seated=paint();
  assert.equal(seated.length,9);
  assert.equal(seated.filter(x=>x.motion==='sit').length,8);
  assert.equal(seatedCrops.length,8,"Todos devem usar o atlas com cadeira real");
  seatedCrops.forEach(({sx,sy,sw,sh,dw,dh})=>{
    assert.deepEqual([sx,sy,sw,sh],[264,88,88,54],
      "Recorte deve mostrar só o personagem, sem a cadeira duplicada");
    assert.equal(dh,Math.round(dw*54/88),
      "Recorte não deve achatar nem esticar a pose sentada");
  });
  seated.slice(0,8).forEach((actual,i)=>{
    const station=map.stations[i];
    assert.equal(actual.motion,"sit","Agente não ficou sentado: "+station.id);
    assert.equal(actual.direction,map.seat.direction);
    assert.equal(actual.frame,3,"Não repetir animação de levantar e sentar");
    assert.equal(actual.x,station.x+map.seat.dx);
    assert.equal(actual.y,station.y+111+map.seat.dy);
    assert.equal(actual.size,map.character.seatedSize,"Escala sentado inconsistente: "+station.id);
  });
  const supervisor=seated.at(-1);
  assert.equal(supervisor.motion,'idle','Subgerente fica em pé sem cadeira fictícia');
  assert.equal(supervisor.size,map.character.standingSize);
  assert.equal(supervisor.x,map.stations[8].x);
  assert.equal(supervisor.y,map.stations[8].y+111);
  // Status de backend não muda a postura de quem está à mesa.
  agents[0].status="trabalhando";
  agents[1].status="revisao";
  assert.equal(paint()[0].motion,"sit");
  assert.equal(paint()[1].motion,"sit");
  agents[0].status="nao_conectado";
  agents[1].status="nao_conectado";

  // A imagem sentada é renderizada independentemente do atlas de walk
  // e do carregamento assíncrono de todas as animações opcionais.
  animatorReady=false;
  assert.equal(paint().length,8);
  animatorReady=true;

  // A caminhada mantém coordenadas, direção e frame; não senta no corredor.
  const walking={moving:true,target:"coffee",motion:"walk",direction:"west",
                 frame:6,x:600,y:460};
  let rendered=paint({agentsList:[agents[0]],routines:{poseFor:id=>id==="diretor"?walking:null}});
  assert.deepEqual(rendered[0],{motion:"walk",direction:"west",frame:6,x:600,y:460,size:84});

  // A pausa no café é em pé, não sentado na cadeira do escritório.
  rendered=paint({agentsList:[agents[0]],routines:{poseFor:id=>id==="diretor"?{
    moving:false,target:"coffee",motion:"idle",direction:"south",
    frame:0,x:857,y:572
  }:null}});
  assert.equal(rendered[0].motion,"idle");
  assert.equal(rendered[0].y,572);
  assert.equal(rendered[0].size,map.character.standingSize);

  // Voltando para casa, o sprite encaixa de novo na cadeira.
  const station=map.stations[0];
  rendered=paint({agentsList:[agents[0]],routines:{poseFor:id=>id==="diretor"?{
    moving:false,target:"home",motion:"sit",direction:"south",frame:0,
    x:station.x,y:station.y+111
  }:null}});
  assert.equal(rendered[0].motion,"sit");
  assert.equal(rendered[0].direction,"north");
  assert.equal(rendered[0].frame,3);
  assert.equal(rendered[0].y,station.y+111+map.seat.dy);
  assert.equal(rendered[0].size,map.character.seatedSize);

  // A prévia manual de outra animação não deve ser bloqueada.
  rendered=paint({selected:"diretor",previewMotion:"wave",agentsList:[agents[0]]});
  assert.equal(rendered[0].motion,"wave");
  assert.equal(rendered[0].y,station.y+111);
  assert.equal(rendered[0].size,map.character.standingSize);

  console.log("AGENT_SEATING_OK: 8 sentados + subgerente em pe, walk preservado");
})().catch(error=>{console.error(error);process.exitCode=1;});
