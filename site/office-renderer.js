/* VideoForge AI — rendering engine: navigation, hit testing, viewport and minimap.
   All original scene artwork lives in office-art.js. */
(() => {
  'use strict';
  const scene=window.VideoForgeArt;
  if(!scene)throw new Error('office-art.js precisa ser carregado antes do renderizador');
  const {W,H,slots}=scene;
  const active=a=>a&&['trabalhando','revisao'].includes(a.status);
  class Office {
    constructor(canvas,onSelect){
      this.canvas=canvas;
      this.ctx=canvas.getContext('2d',{alpha:false});
      if(!this.ctx)throw new Error('Canvas 2D indisponível');
      this.onSelect=onSelect;
      this.agents=[];this.selected=null;this.zoom=1;this.panX=0;this.panY=0;
      this.pointerMap=new Map();this.drag=null;this.pinch=null;this.wasMobile=null;
      this.miniCanvas=null;this.miniCtx=null;
      this.bg=document.createElement('canvas');this.bg.width=W;this.bg.height=H;
      scene.paintBackground(this.bg.getContext('2d'));
      this.reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      this.resizeObserver=typeof ResizeObserver!=='undefined'?new ResizeObserver(()=>this.resize()):null;
      if(this.resizeObserver)this.resizeObserver.observe(canvas.parentElement);
      else window.addEventListener('resize',()=>this.resize());
      canvas.addEventListener('pointerdown',e=>this.pointerDown(e));
      canvas.addEventListener('pointermove',e=>this.pointerMove(e));
      canvas.addEventListener('pointerup',e=>this.pointerUp(e));
      canvas.addEventListener('pointercancel',e=>this.pointerUp(e,true));
      canvas.addEventListener('lostpointercapture',e=>{this.pointerMap.delete(e.pointerId);this.drag=null;this.pinch=null;});
      canvas.addEventListener('wheel',e=>{
        e.preventDefault();const p=this.localPointer(e);
        this.zoomAt(e.deltaY<0?1.12:1/1.12,p.x,p.y);
      },{passive:false});
      this.resize();
      this.lastFrame=0;
      const loop=(ts)=>{
        const moving=this.agents.some(active)&&!this.reduceMotion;
        const fps=moving?10:3;
        if(ts-this.lastFrame>=1000/fps){this.render(ts);this.lastFrame=ts;}
        this.frame=requestAnimationFrame(loop);
      };
      this.frame=requestAnimationFrame(loop);
    }
    setAgents(list){this.agents=list.slice(0,slots.length);this.render(0);}
    setSelected(id){this.selected=id;this.render(0);}
    setArtMode(mode){
      if(!scene.setArtMode(mode))return false;
      scene.paintBackground(this.bg.getContext('2d'));
      this.reset();this.renderMiniMap();
      return true;
    }
    getArtMode(){return scene.getArtMode();}
    setMiniMap(canvas){
      this.miniCanvas=canvas;
      this.miniCtx=canvas.getContext('2d');
      canvas.addEventListener('click',e=>{
        const bounds=canvas.getBoundingClientRect();
        const x=(e.clientX-bounds.left)/bounds.width*W;
        const y=(e.clientY-bounds.top)/bounds.height*H;
        this.centerWorld(x,y);this.render(0);
      });
      this.renderMiniMap();
    }
    viewport(){
      const scale=Math.min(this.viewW/W,this.viewH/H)*this.zoom;
      return {scale,x:(this.viewW-W*scale)/2+this.panX,y:(this.viewH-H*scale)/2+this.panY};
    }
    defaultZoom(){
      const fit=Math.min(this.viewW/W,this.viewH/H);
      if(this.viewW>700)return 1;
      const suggested=Math.min(4.2,Math.max(1.3,(this.viewH/(H*.96))/fit));
      return scene.getArtMode()==='pixellab'?Math.min(suggested,3):suggested;
    }
    resize(){
      const bounds=this.canvas.parentElement.getBoundingClientRect();
      this.viewW=Math.max(1,bounds.width);this.viewH=Math.max(1,bounds.height);
      const dpr=Math.min(window.devicePixelRatio||1,2);
      this.canvas.width=Math.round(this.viewW*dpr);this.canvas.height=Math.round(this.viewH*dpr);
      this.canvas.style.width=this.viewW+'px';this.canvas.style.height=this.viewH+'px';this.dpr=dpr;
      const mobile=this.viewW<=700;
      if(this.wasMobile===null||mobile!==this.wasMobile){
        this.wasMobile=mobile;this.zoom=this.defaultZoom();this.panX=0;this.panY=0;
        if(mobile)this.centerWorld(scene.getArtMode()==='pixellab'?335:438,420);
      }
      this.render(0);
    }
    reset(){this.zoom=this.defaultZoom();this.panX=0;this.panY=0;if(this.viewW<=700)this.centerWorld(scene.getArtMode()==='pixellab'?335:438,420);this.render(0);}
    centerWorld(worldX,worldY){
      const v=this.viewport();
      this.panX+=(this.viewW/2-v.x-worldX*v.scale);
      this.panY+=(this.viewH/2-v.y-worldY*v.scale);
      this.limitPan();
    }
    focusAgent(id){
      const idx=this.agents.findIndex(a=>a.id===id);
      if(idx<0)return;
      if(this.viewW<=700)this.centerWorld(slots[idx][0],slots[idx][1]+98);
      this.render(0);
    }
    zoomAt(mult,cx=this.viewW/2,cy=this.viewH/2){
      const p=this.toWorld(cx,cy);
      this.zoom=Math.max(.78,Math.min(4.2,this.zoom*mult));
      const v=this.viewport();
      this.panX+=cx-(v.x+p.x*v.scale);
      this.panY+=cy-(v.y+p.y*v.scale);
      this.limitPan();this.render(0);
    }
    limitPan(){
      const v=this.viewport();
      const maxX=Math.max(24,(W*v.scale-this.viewW)/2+44);
      const maxY=Math.max(24,(H*v.scale-this.viewH)/2+44);
      this.panX=Math.min(maxX,Math.max(-maxX,this.panX));
      this.panY=Math.min(maxY,Math.max(-maxY,this.panY));
    }
    toWorld(x,y){const v=this.viewport();return {x:(x-v.x)/v.scale,y:(y-v.y)/v.scale};}
    localPointer(e){const r=this.canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
    agentAt(x,y){
      const p=this.toWorld(x,y);
      if(this.getArtMode()==='pixellab'){
        let best=null,bestDistance=Infinity;
        for(let i=0;i<this.agents.length;i++){
          const [sx,sy]=slots[i],dx=p.x-sx,dy=p.y-(sy+111);
          const distance=Math.hypot(dx,dy);
          if(Math.abs(dx)<=68&&Math.abs(dy)<=67&&distance<bestDistance){
            best=this.agents[i].id;bestDistance=distance;
          }
        }
        return best;
      }
      for(let i=0;i<this.agents.length;i++){
        const [sx,sy]=slots[i];
        if(Math.abs(p.x-sx)<=69&&p.y>sy-38&&p.y<sy+206)return this.agents[i].id;
      }
      return null;
    }
    pointerDown(e){
      e.preventDefault();const p=this.localPointer(e);
      this.canvas.setPointerCapture(e.pointerId);this.pointerMap.set(e.pointerId,p);
      this.drag={id:e.pointerId,startX:p.x,startY:p.y,moved:false};
      if(this.pointerMap.size===2)this.startPinch();
    }
    startPinch(){const pts=Array.from(this.pointerMap.values());this.pinch={dist:Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y),zoom:this.zoom};this.drag=null;}
    pointerMove(e){
      const previous=this.pointerMap.get(e.pointerId);if(!previous)return;
      const p=this.localPointer(e),dx=p.x-previous.x,dy=p.y-previous.y;
      this.pointerMap.set(e.pointerId,p);
      if(this.pointerMap.size>1){
        const pts=Array.from(this.pointerMap.values());
        if(this.pinch){const dist=Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y);
          const target=this.pinch.zoom*(dist/Math.max(1,this.pinch.dist));
          this.zoomAt(target/this.zoom,(pts[0].x+pts[1].x)/2,(pts[0].y+pts[1].y)/2);
        }
        return;
      }
      if(this.drag&&this.drag.id===e.pointerId){
        this.panX+=dx;this.panY+=dy;this.limitPan();
        if(Math.hypot(p.x-this.drag.startX,p.y-this.drag.startY)>8)this.drag.moved=true;
        this.render(0);
      }
    }
    pointerUp(e,cancel=false){
      const p=this.pointerMap.get(e.pointerId);
      if(!cancel&&p&&this.drag&&!this.drag.moved&&this.drag.id===e.pointerId){
        const id=this.agentAt(p.x,p.y);if(id)this.onSelect(id);
      }
      this.pointerMap.delete(e.pointerId);
      this.drag=null;if(this.pointerMap.size<2)this.pinch=null;
    }
    render(ts){
      if(!this.viewW||!this.viewH)return;
      const c=this.ctx,d=this.dpr;
      c.setTransform(d,0,0,d,0,0);
      c.fillStyle='#111b2a';c.fillRect(0,0,this.viewW,this.viewH);
      const v=this.viewport();
      c.save();c.translate(v.x,v.y);c.scale(v.scale,v.scale);c.imageSmoothingEnabled=false;
      c.drawImage(this.bg,0,0);
      scene.paintAgents(c,this.agents,this.selected,ts);
      c.restore();this.renderMiniMap();
    }
    renderMiniMap(){
      if(!this.miniCtx)return;
      const c=this.miniCtx,mini=this.miniCanvas,mw=mini.width,mh=mini.height;
      c.clearRect(0,0,mw,mh);c.imageSmoothingEnabled=false;
      c.drawImage(this.bg,0,0,W,H,0,0,mw,mh);
      this.agents.forEach((a,i)=>{
        const [x,y]=slots[i];
        c.fillStyle=a.id===this.selected?'#f5cd83':active(a)?'#98f5be':'#edf2df';
        c.fillRect(x/W*mw-2,y/H*mh-2,5,5);
      });
      const v=this.viewport();if(!v.scale)return;
      const x=(-v.x/v.scale)/W*mw,y=(-v.y/v.scale)/H*mh;
      const w=(this.viewW/v.scale)/W*mw,h=(this.viewH/v.scale)/H*mh;
      c.strokeStyle='#fff0c4';c.lineWidth=2;c.strokeRect(x,y,w,h);
    }
  }
  window.VideoForgeOffice={Office,WORLD_WIDTH:W,WORLD_HEIGHT:H};
})();
