"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
global.window={};
const manifest=JSON.parse(fs.readFileSync("site/assets/pixellab/agents/alex/manifest.json","utf8"));
manifest.motions.walk={...manifest.motions.walk,width:704,height:704,frames:8};
global.fetch=async()=>({ok:true,json:async()=>manifest});
global.Image=class{
    constructor(){this.onload=null;this.onerror=null;this.naturalWidth=0;this.naturalHeight=0;}
    set src(url){
        const name=url.split("/").at(-1).replace(".png","");
        this.naturalWidth=manifest.motions[name].width;
        this.naturalHeight=manifest.motions[name].height;
        if(this.onload)this.onload();
    }
};
require("../site/agent-animator.js");
(async()=>{
    const animator=window.VideoForgeAnimator;
    assert.equal(await animator.preload(),true);
    assert.equal(animator.frameCount("walk"),8);
    assert.equal(animator.frameCount("idle"),4);
    const calls=[];
    const ctx={drawImage:(...args)=>calls.push(args)};
    assert.equal(animator.draw(ctx,"walk","north",7,200,200),true);
    assert.equal(calls[0][1],7*88,"oitavo quadro de walk deve aparecer");
    assert.equal(calls[0][2],4*88,"direção north deve usar a quinta linha");
    assert.equal(animator.draw(ctx,"walk","north",8,200,200),true);
    assert.equal(calls[1][1],0,"ciclo de oito quadros deve repetir");
    assert.equal(animator.draw(ctx,"talk","north",7,200,200),true);
    assert.equal(calls[2][1],3*88,"outros movimentos permanecem com quatro quadros");
    console.log("WALK_RENDER_8_FRAMES_OK");
})().catch(err=>{console.error(err);process.exitCode=1;});
