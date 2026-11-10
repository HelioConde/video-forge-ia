/* Garante que toda função use sprites realmente catalogados e preserve status. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const manifest=JSON.parse(fs.readFileSync("site/assets/pixellab/agents/alex/production/manifest.json","utf8"));
global.window={};
require("../site/agent-behavior.js");
const model=window.VideoForgeBehaviors;
const available=new Set(Object.keys(manifest.motions));
assert.equal(model.roles.length,8);
for(const role of model.roles){
  const profile=model.profile(role);
  assert(profile);
  assert(profile.work.length>=3);
  assert(profile.demo.length>=3);
  assert(model.names(role).every(m=>available.has(m)),"animação não importada: "+role);
  const idle={id:role,status:"nao_conectado"};
  assert.equal(model.choose(idle,10000,false,m=>available.has(m)),"idle");
  assert(model.names(role).includes(model.choose(idle,10000,true,m=>available.has(m))));
  const live={id:role,status:"trabalhando"};
  assert(model.names(role).includes(model.choose(live,10000,false,m=>available.has(m))));
  assert.equal(model.choose({id:role,status:"erro"},10000,true,m=>available.has(m)),"idle");
}
const example=Object.fromEntries(model.roles.map(id=>[id,model.choose({id,status:"trabalhando"},10000,false,m=>available.has(m))]));
console.log("MOVIMENTOS_PROFISSOES_OK "+JSON.stringify(example));
