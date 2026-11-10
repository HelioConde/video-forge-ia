"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
global.window={};
require("../site/agent-interactions.js");
const interactions=window.VideoForgeInteractions;
const catalog=JSON.parse(fs.readFileSync("personagens/alex/production-animations.json","utf8"));
const manifest=JSON.parse(fs.readFileSync("site/assets/pixellab/agents/alex/production/manifest.json","utf8"));
for(const target of interactions.targets){
  const s=interactions.steps(target);
  assert(s.length>=5,"sequência de rotina insuficiente: "+target);
  assert(interactions.duration(target)>2000,"sequência sem duração própria");
  const start=interactions.sample(target,0);
  assert.equal(start.motion,s[0].motion);
  assert.equal(interactions.sample(target,interactions.duration(target)),null);
  assert(interactions.motions(target).every(m=>manifest.motions[m]),
    "Sequência aponta para sprite de personagem não importado: "+target);
}
assert.equal(Object.keys(interactions.composites).length,12);
const sequences=catalog.items.filter(x=>x.kind==="sequence").map(x=>x.motion);
assert.deepEqual(sequences.sort(),Object.keys(interactions.composites).sort());
assert.equal(interactions.composites.use_elevator.availability,"blocked_no_elevator");
console.log("INTERACOES_DEMO_OK: 5 rotinas completas, 12 sequências mapeadas, elevador bloqueado");