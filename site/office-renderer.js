/* VideoForge AI Pixel Office — desenho original Canvas 2D, sem assets externos. */
(() => {
  "use strict";
  const W = 1280, H = 820;
  const SLOTS = [
    [173, 290], [355, 290], [537, 290], [719, 290],
    [173, 526], [355, 526], [537, 526], [719, 526]
  ];
  const SHIRTS = ["#9b93e8","#edb86f","#70caa9","#ea8b9a","#6bb9e5","#e89d6e","#a4c77a","#67c5bd"];
  const HAIR = ["#302538","#6d402d","#332c40","#bb7146","#272c3e","#5a332d","#d8b17a","#282c37"];
  const SKIN = ["#e4ac82","#c78c66","#eec49c","#b67c5e","#d1a17e","#f0bb8c","#b98263","#d89c75"];
  const FONT = "'Courier New',monospace";
  const box = (c,x,y,w,h,color) => { c.fillStyle=color; c.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h)); };
  const stroke = (c,x,y,w,h,color,lw=2) => {c.lineWidth=lw;c.strokeStyle=color;c.strokeRect(Math.round(x)+.5,Math.round(y)+.5,Math.round(w),Math.round(h));};
  const txt = (c,s,x,y,color="#e9e4d8",size=12,align="left") => {c.fillStyle=color;c.font="bold "+size+"px "+FONT;c.textAlign=align;c.textBaseline="alphabetic";c.fillText(s,x,y);};
  const hash = (a,b) => ((a*73856093 ^ b*19349663)>>>0)%97;
  const rr = (c,x,y,w,h,r,color) => {c.fillStyle=color;c.beginPath();c.roundRect(x,y,w,h,r);c.fill();};

  function plant(c,x,y,size=1) {
    c.save();c.translate(x,y);c.scale(size,size);
    box(c,-10,4,20,14,"#513a3b");box(c,-7,4,14,4,"#a47857");box(c,-2,-26,4,32,"#345947");
    for(const [dx,dy,color] of [[-16,-18,"#459568"],[13,-24,"#57ac72"],[-9,-33,"#79be79"],[8,-39,"#4c985f"],[-19,-32,"#3d755c"],[19,-12,"#8cc77c"]]){box(c,dx-4,dy-3,10,14,color);box(c,dx-1,dy-9,5,7,color);}
    c.restore();
  }
  function windowArt(c,x,y) {
    box(c,x,y,122,64,"#1b293b");box(c,x+6,y+6,110,52,"#9bc8d6");
    box(c,x+6,y+30,110,28,"#78a69b");box(c,x+6,y+42,110,16,"#446f78");
    box(c,x+8,y+32,30,13,"#8bb4aa");box(c,x+60,y+25,30,16,"#b7d7c9");
    box(c,x+59,y+7,9,51,"#253447");box(c,x+6,y+34,110,7,"#253447");box(c,x-4,y+60,130,7,"#506475");
  }
  function shelf(c,x,y) {
    box(c,x-4,y-4,121,62,"#342d3a");box(c,x,y,113,55,"#8d5f45");
    for(let row=0;row<2;row++){
      box(c,x+4,y+row*26+21,105,4,"#d1a273");
      for(let i=0;i<10;i++){
        const colors=["#84a9b6","#bd777b","#c9a56e","#78a389","#ac91b9","#ddad74"];
        box(c,x+7+i*10,y+3+row*26+(i%3)*2,7,17-(i%3)*2,colors[(i+row*3)%colors.length]);
      }
    }
    box(c,x-6,y+56,125,6,"#452e36");
  }
  function monitor(c,x,y,lit=false) {
    box(c,x-24,y-20,49,35,"#172638");
    box(c,x-20,y-16,41,27,lit?"#27575c":"#32505b");
    box(c,x-15,y-9,19,3,lit?"#88efb5":"#6b9eab");
    box(c,x-15,y-2,29,2,lit?"#76d5aa":"#628a9a");
    box(c,x-15,y+4,14,2,"#84b2b7");
    box(c,x-3,y+15,8,7,"#344052");box(c,x-17,y+22,34,4,"#26384b");
  }
  function desk(c,x,y) {
    box(c,x-57,y-16,118,69,"#543c38");box(c,x-61,y-22,125,66,"#9e704e");
    box(c,x-56,y-17,115,54,"#bf9168");
    box(c,x-52,y-14,107,4,"#d4a47a");
    box(c,x-52,y+35,112,6,"#825641");
    box(c,x-52,y+40,12,13,"#674439");box(c,x+45,y+40,13,13,"#674439");
    box(c,x-9,y+52,25,19,"#4c5267");box(c,x-11,y+57,28,7,"#778097");
    box(c,x-51,y+10,16,19,"#ddceb3");box(c,x-48,y+13,12,2,"#a4a9a0");box(c,x-48,y+18,9,2,"#a4a9a0");
    monitor(c,x+6,y+2);
    box(c,x+33,y+17,19,13,"#425362");box(c,x+36,y+20,13,6,"#c7d0cd");
    box(c,x+32,y-12,10,11,"#6eaa9b");box(c,x+34,y-16,6,6,"#cfe4b9");
  }
  function couch(c,x,y,w=160) {
    box(c,x-7,y-8,w+14,62,"#2e3554");box(c,x,y,w,45,"#677b9a");
    box(c,x+8,y+8,w-16,31,"#8196b5");box(c,x+9,y+8,3,34,"#adb8cd");
    box(c,x+w-12,y+8,3,34,"#adb8cd");box(c,x+9,y+40,w-18,10,"#53667d");
    box(c,x-8,y+9,18,39,"#536681");box(c,x+w-10,y+9,18,39,"#536681");
  }
  function officeBackground(c) {
    box(c,0,0,W,H,"#111a2a");
    for(let x=0;x<W;x+=28){box(c,x,0,1,H,"#1a2636");}
    box(c,25,22,1230,777,"#132331");box(c,39,35,1202,749,"#425063");
    box(c,51,47,1178,730,"#293b4d");box(c,58,51,1164,90,"#314257");
    for(let x=62;x<1226;x+=33){box(c,x,52,2,85,"#41556a");}
    box(c,58,136,1164,620,"#99704f");
    // Laminado de madeira, sem textura de terceiros.
    for(let y=142;y<753;y+=26){
      box(c,59,y,1163,2,y%52?"#ad8059":"#795b48");
      let start=62+(hash(7,y)%5)*24;
      for(let x=start;x<1222;x+=120){
        box(c,x,y,2,25,"#845f47");box(c,x+4,y+5,2,2,"#c49a69");
        if(hash(x,y)%6===0)box(c,x+53,y+11,12,2,"#8f654e");
      }
    }
    box(c,58,136,1164,8,"#4a3a40");
    box(c,58,751,1164,12,"#362f3b");box(c,58,763,1164,6,"#b28b65");
    // Paredes e janelas.
    shelf(c,76,67);windowArt(c,268,62);windowArt(c,430,62);windowArt(c,592,62);
    box(c,763,70,220,44,"#1c2939");stroke(c,766,73,214,38,"#7ca5a9",4);
    txt(c,"VIDEOFORGE",873,94,"#b9f1de",22,"center");
    box(c,803,106,161,3,"#4fa9a6");
    box(c,1021,60,176,59,"#182c3d");box(c,1029,66,160,45,"#deceb0");
    txt(c,"STUDIO  /  HQ",1109,86,"#405265",14,"center");
    txt(c,"PIXEL OFFICE",1109,103,"#617781",12,"center");
    // Divisória para lounge de produção.
    box(c,825,143,11,609,"#394658");box(c,836,143,6,609,"#1c2b3f");
    box(c,822,430,18,72,"#99704f"); // porta de passagem
    box(c,838,433,4,66,"#d6b17f");
    box(c,845,147,368,290,"#50647c");
    for(let y=148;y<434;y+=40){box(c,845,y,367,2,"#60758b");}
    box(c,858,177,338,237,"#344962");stroke(c,857,177,339,237,"#1c2c3c",7);
    // Tapete e mobiliário da sala de reunião.
    box(c,870,230,310,163,"#486580");stroke(c,870,230,310,163,"#7891a5",6);
    couch(c,888,246,176);couch(c,1051,337,112);
    box(c,960,317,118,48,"#604c4b");box(c,965,309,109,48,"#bd986d");
    box(c,1005,329,28,11,"#e2d3ab");box(c,1039,323,16,17,"#468997");
    plant(c,879,224,1.05);plant(c,1170,225,1.08);
    shelf(c,1074,160);
    // Estúdio de gravação do lado direito.
    box(c,851,490,352,242,"#334b54");stroke(c,854,491,346,239,"#667d7e",6);
    box(c,874,516,310,195,"#475960");stroke(c,874,516,310,195,"#799294",4);
    box(c,898,548,131,105,"#1e2d3c");box(c,905,555,118,88,"#789eab");
    box(c,912,562,104,42,"#2f506c");box(c,918,610,30,27,"#cc846b");
    box(c,960,610,46,27,"#688d9c");txt(c,"REC",965,628,"#eaccc4",12);
    box(c,1054,555,98,14,"#bb9a69");box(c,1060,568,86,52,"#896746");
    box(c,1064,574,80,32,"#aa8b61");box(c,1095,577,22,27,"#324557");
    box(c,1098,583,16,13,"#6bdcbf");
    box(c,1033,657,120,19,"#2f3647");box(c,1041,669,105,15,"#c0a77a");
    plant(c,861,693,.8);plant(c,1181,684,.85);
    // Tapetes individuais e placas dos postos: diferencia as áreas de trabalho.
    SLOTS.forEach(([x,y],i)=>{
      const rug=i%2===0?"#8d745e":"#8b7058";
      box(c,x-79,y-52,159,229,"#634e48");
      box(c,x-75,y-48,151,221,rug);
      stroke(c,x-75,y-48,151,221,i%2===0?"#bc9972":"#b19072",3);
      for(let d=0;d<4;d++) box(c,x-65+d*40,y+162,25,2,"#b59a7c");
      box(c,x-62,y-45,125,20,"#293a4b");
      txt(c,"POSTO "+String(i+1).padStart(2,"0"),x,y-31,"#dae4d5",11,"center");
    });
    for (const [x,y] of SLOTS)desk(c,x,y);
    // TV e quadros na parede lateral
    box(c,65,184,70,52,"#203143");box(c,70,189,60,41,"#8aafaa");
    box(c,77,204,39,7,"#e9ca8f");box(c,82,218,46,3,"#517c84");
    plant(c,86,730,.9);plant(c,792,720,.9);
    // Sinalizações da sala.
    box(c,72,397,73,28,"#273644");txt(c,"PROD.",108,415,"#a5f2d2",13,"center");
    box(c,861,453,328,28,"#233646");txt(c,"REUNIÕES  /  DIREÇÃO CRIATIVA",1025,472,"#d1d2bd",13,"center");
    txt(c,"ÁUDIO  /  EDIÇÃO",1030,718,"#d1d8c4",13,"center");
    // Detalhes cenográficos: quadros, relógio, prateleiras, console de áudio e LEDs.
    box(c,975,174,82,45,"#182a3c");stroke(c,975,174,82,45,"#8ba4a2",3);
    txt(c,"PLANO",1016,189,"#bde2d4",12,"center");
    for(let i=0;i<3;i++){box(c,985,196+i*6,8,3,["#9ee2ae","#f0ca8a","#a4cde5"][i]);box(c,998,196+i*6,47-i*7,2,"#7798a3");}
    for(let i=0;i<6;i++){box(c,1080+i*15,629-(i%4)*6,8,13+(i%4)*6,["#9ebfd0","#7fbda5","#d3ad86"][i%3]);}
    box(c,1049,625,111,4,"#243c48");
    for(let i=0;i<4;i++){box(c,102+i*128,172,45,4,"#e5d1a2");box(c,102+i*128,176,45,3,"#675c58");}
    // Moldura do escritório.
    box(c,39,32,1204,13,"#101e2e");box(c,39,775,1204,14,"#101e2e");
    box(c,39,32,14,757,"#101e2e");box(c,1229,32,14,757,"#101e2e");
    stroke(c,43,36,1196,744,"#708090",3);
  }
  function character(c,x,y,i,stamp,active,selected) {
    const sx=Math.round(x),sy=Math.round(y);
    const skin=SKIN[i%SKIN.length],hair=HAIR[i%HAIR.length],shirt=SHIRTS[i%SHIRTS.length];
    // Micro movimento visual apenas para identificação do sprite, sem fingir atividade.
    const idle=active ? Math.floor(stamp/420)%2 : 0;
    box(c,sx-16,sy+24,35,6,"#4d3b39");
    box(c,sx-14,sy+17-idle,12,13,"#36455b");box(c,sx+5,sy+17-idle,12,13,"#36455b");
    box(c,sx-14,sy+27,12,5,"#2a303d");box(c,sx+5,sy+27,12,5,"#2a303d");
    box(c,sx-17,sy-2-idle,36,26,"#252d3e");
    box(c,sx-13,sy+1-idle,28,22,shirt);
    box(c,sx-22,sy+5-idle,9,15,skin);box(c,sx+15,sy+5-idle,9,15,skin);
    box(c,sx-12,sy-26-idle,29,28,skin);
    box(c,sx-16,sy-29-idle,37,10,hair);
    box(c,sx-16,sy-20-idle,8,12,hair);box(c,sx+16,sy-20-idle,6,9,hair);
    box(c,sx-4,sy-11-idle,3,3,"#2d2630");
    box(c,sx+9,sy-11-idle,3,3,"#2d2630");
    box(c,sx+1,sy-5-idle,6,2,"#9d644e");
    if(i===0){box(c,sx-18,sy-29-idle,41,6,"#25243c");box(c,sx-5,sy-10-idle,18,4,"#d2b2e9");}
    if(i===4){box(c,sx-8,sy+1-idle,18,6,"#f3dd9a");}
    if(active){box(c,sx+22,sy+5-idle,7,7,"#a9f5b5");box(c,sx-26,sy+7,7,7,skin);}
    if(selected){stroke(c,sx-28,sy-37,58,76,"#fff1a1",3);box(c,sx-5,sy-47,12,8,"#f6cf77");}
  }
  function bubble(c,x,y,s,color) {
    const w=Math.max(99,Math.min(164,20+s.length*7));
    rr(c,x-w/2,y-13,w,23,5,"#192b3c");
    stroke(c,x-w/2,y-13,w,23,color,2);
    txt(c,s,x,y+3,"#e3e8e3",12,"center");
  }
  function agentSprites(c,agents,selected,t) {
    agents.forEach((a,i)=>{
      const slot=SLOTS[i];if(!slot)return;
      const [x,y]=slot;const doing=["trabalhando","revisao"].includes(a.status);
      // O monitor só ganha realce se status do backend permitir.
      if(doing)box(c,x+1,y-11,24,3,"#9bedbf");
      character(c,x,y+73,i,t,doing,selected===a.id);
      const nick=a.nome?.length>15 ? a.nome.slice(0,14)+"…" : (a.nome||a.id);
      bubble(c,x,y+132,nick,doing?"#76dbac":selected===a.id?"#f5cc72":"#6e8291");
      const color=doing?"#9fe8b0":a.status==="erro"?"#ef8e82":a.status==="aguardando"?"#eac47e":"#bac5ca";
      box(c,x-42,y+146,7,7,color);txt(c,a.status==="nao_conectado"?"offline":a.status==="trabalhando"?"trabalhando":a.status==="revisao"?"revisão":a.status==="concluido"?"concluído":a.status==="erro"?"erro":"aguardando",x-28,y+153,color,11);
    });
  }
  class Office {
    constructor(canvas, onSelect) {
      this.canvas=canvas;this.ctx=canvas.getContext("2d",{alpha:false});
      if(!this.ctx)throw new Error("Canvas 2D indisponível");
      this.onSelect=onSelect;this.agents=[];this.selected=null;this.miniCanvas=null;this.miniCtx=null;
      this.zoom=1;this.panX=0;this.panY=0;this.last=0;this.pointerMap=new Map();this.drag=null;this.pinch=null;
      this.bg=document.createElement("canvas");this.bg.width=W;this.bg.height=H;
      officeBackground(this.bg.getContext("2d"));
      this.resizeObserver=new ResizeObserver(()=>this.resize());
      this.resizeObserver.observe(canvas.parentElement);
      canvas.addEventListener("pointerdown",e=>this.pointerDown(e));
      canvas.addEventListener("pointermove",e=>this.pointerMove(e));
      canvas.addEventListener("pointerup",e=>this.pointerUp(e));
      canvas.addEventListener("pointercancel",e=>this.pointerUp(e));
      canvas.addEventListener("lostpointercapture",e=>{this.pointerMap.delete(e.pointerId);this.drag=null;this.pinch=null});
      canvas.addEventListener("wheel",e=>{e.preventDefault();this.zoomAt(e.deltaY<0?1.12:1/1.12,e.offsetX,e.offsetY);},{passive:false});
      this.resize();
      this.loop=(ts)=>{if(ts-this.last>33){this.render(ts);this.last=ts}this.frame=requestAnimationFrame(this.loop);};
      this.frame=requestAnimationFrame(this.loop);
    }
    setAgents(agents){this.agents=agents.slice(0,SLOTS.length)}
    setSelected(id){this.selected=id}
    setMiniMap(canvas){
      this.miniCanvas=canvas;this.miniCtx=canvas.getContext("2d");
      canvas.addEventListener("click",e=>{
        const rect=canvas.getBoundingClientRect();
        const x=(e.clientX-rect.left)/rect.width*W;
        const y=(e.clientY-rect.top)/rect.height*H;
        this.centerWorld(x,y);
      });
    }
    defaultZoom(){
      const fit=Math.min(this.viewW/W,this.viewH/H);
      if(this.viewW>700)return 1;
      // No celular, a sala preenche a altura. É possível explorar as laterais com arraste e minimapa.
      return Math.min(4.2,Math.max(1.3,(this.viewH/(H*.96))/fit));
    }
    centerWorld(worldX,worldY){
      const scale=this.viewport().scale;
      this.panX=(W/2-worldX)*scale;
      this.panY=(H/2-worldY)*scale;
      this.limitPan();
    }
    focusAgent(id){
      const i=this.agents.findIndex(a=>a.id===id);
      if(i<0)return;
      if(this.viewW<=700)this.centerWorld(SLOTS[i][0],SLOTS[i][1]+58);
    }
    viewport(){const scale=Math.min(this.viewW/W,this.viewH/H)*this.zoom;return {scale,x:(this.viewW-W*scale)/2+this.panX,y:(this.viewH-H*scale)/2+this.panY};}
    resize(){const rect=this.canvas.parentElement.getBoundingClientRect();this.viewW=Math.max(1,rect.width);this.viewH=Math.max(1,rect.height);
      const dpr=Math.min(window.devicePixelRatio||1,2);this.canvas.width=Math.round(this.viewW*dpr);this.canvas.height=Math.round(this.viewH*dpr);
      this.canvas.style.width=this.viewW+"px";this.canvas.style.height=this.viewH+"px";this.dpr=dpr;
      const mobile=this.viewW<=700;
      if(!this.initialized || mobile!==this.wasMobile){
        this.zoom=this.defaultZoom();this.panX=0;this.panY=0;
        this.initialized=true;this.wasMobile=mobile;
        if(mobile)this.centerWorld(445,410);
      }
    }
    reset(){
      this.zoom=this.defaultZoom();this.panX=0;this.panY=0;
      if(this.viewW<=700)this.centerWorld(445,410);
    }
    zoomAt(mult,cx=this.viewW/2,cy=this.viewH/2){const before=this.viewport(),px=(cx-before.x)/before.scale,py=(cy-before.y)/before.scale;
      this.zoom=Math.max(.7,Math.min(4.2,this.zoom*mult));
      const after=this.viewport();this.panX+=(cx-after.x)-px*after.scale;this.panY+=(cy-after.y)-py*after.scale;
      this.limitPan();
    }
    limitPan(){
      const {scale}=this.viewport();
      const maxX=Math.max(30,(W*scale-this.viewW)/2+32);
      const maxY=Math.max(30,(H*scale-this.viewH)/2+32);
      this.panX=Math.min(Math.max(this.panX,-maxX),maxX);
      this.panY=Math.min(Math.max(this.panY,-maxY),maxY);
    }
    toWorld(x,y){const v=this.viewport();return {x:(x-v.x)/v.scale,y:(y-v.y)/v.scale};}
    agentAt(x,y){const p=this.toWorld(x,y);for(let i=0;i<this.agents.length;i++){const [ax,ay]=SLOTS[i];if(Math.abs(p.x-ax)<72 && p.y>ay-55 && p.y<ay+165)return this.agents[i].id;}return null;}
    pointerDown(e){e.preventDefault();this.canvas.setPointerCapture(e.pointerId);this.pointerMap.set(e.pointerId,{x:e.offsetX,y:e.offsetY});
      this.drag={id:e.pointerId,x:e.offsetX,y:e.offsetY,originX:e.offsetX,originY:e.offsetY,moved:false};
      if(this.pointerMap.size===2)this.startPinch();
    }
    startPinch(){const p=Array.from(this.pointerMap.values());const dist=Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);this.pinch={dist,zoom:this.zoom};this.drag=null;}
    pointerMove(e){if(!this.pointerMap.has(e.pointerId))return;
      const p=this.pointerMap.get(e.pointerId),dx=e.offsetX-p.x,dy=e.offsetY-p.y;p.x=e.offsetX;p.y=e.offsetY;
      if(this.pointerMap.size>1){const pts=Array.from(this.pointerMap.values());const dist=Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y);if(this.pinch&&this.pinch.dist>0){const target=this.pinch.zoom*dist/this.pinch.dist;const midpointX=(pts[0].x+pts[1].x)/2,midpointY=(pts[0].y+pts[1].y)/2;this.zoomAt(target/this.zoom,midpointX,midpointY);}return;}
      if(this.drag&&this.drag.id===e.pointerId){this.panX+=dx;this.panY+=dy;this.limitPan();if(Math.hypot(e.offsetX-this.drag.originX,e.offsetY-this.drag.originY)>7)this.drag.moved=true;}
    }
    pointerUp(e){const p=this.pointerMap.get(e.pointerId);if(p&&this.drag&&this.drag.id===e.pointerId&&!this.drag.moved){const hit=this.agentAt(e.offsetX,e.offsetY);if(hit)this.onSelect(hit);}
      this.pointerMap.delete(e.pointerId);this.drag=null;if(this.pointerMap.size<2)this.pinch=null;
    }
    render(t){const c=this.ctx,d=this.dpr;c.setTransform(d,0,0,d,0,0);
      box(c,0,0,this.viewW,this.viewH,"#101827");
      const v=this.viewport();c.save();c.translate(v.x,v.y);c.scale(v.scale,v.scale);c.imageSmoothingEnabled=false;
      c.drawImage(this.bg,0,0);agentSprites(c,this.agents,this.selected,t);c.restore();
      this.renderMiniMap();
    }
    renderMiniMap(){
      if(!this.miniCanvas || !this.miniCtx)return;
      const mini=this.miniCanvas,ctx=this.miniCtx;
      const mw=mini.width,mh=mini.height;
      ctx.imageSmoothingEnabled=false;
      ctx.clearRect(0,0,mw,mh);
      ctx.drawImage(this.bg,0,0,W,H,0,0,mw,mh);
      this.agents.forEach((a,i)=>{
        const slot=SLOTS[i];if(!slot)return;
        ctx.fillStyle=a.id===this.selected?"#f4d488":(["trabalhando","revisao"].includes(a.status)?"#a5f6b7":"#e5f0db");
        ctx.fillRect(slot[0]/W*mw-2,slot[1]/H*mh-2,5,5);
      });
      const v=this.viewport();
      let x=(-v.x/v.scale)/W*mw,y=(-v.y/v.scale)/H*mh;
      let w=(this.viewW/v.scale)/W*mw,h=(this.viewH/v.scale)/H*mh;
      ctx.strokeStyle="#fff3c7";ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);
    }
  }
  window.VideoForgeOffice={Office, WORLD_WIDTH:W, WORLD_HEIGHT:H};
})();