/* Testa assentos do cenário: nenhum agent na faixa de janelas/fora da sala. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const source=fs.readFileSync("site/office-art.js","utf8");
const match=source.match(/const pixelStations=(\[\[.*?\]\]);/);
assert(match,"O cenário precisa declarar suas âncoras PixelLab");
const places=JSON.parse(match[1]);
assert.equal(places.length,8);
assert.equal(new Set(places.map(p=>p.join(","))).size,8,"Dois agents dividem a mesma cadeira");
const xLeft=79,xRight=591,top=194,bottom=706;
for(const [index,p] of places.entries()){
  const [x,y]=p,at=y+111;
  assert(x>=(xLeft+36)&&x<=(xRight-36),"Personagem fora da sala "+index);
  assert(at-36>=top+85,"Personagem invadindo janelas "+index);
  assert(at+67<=bottom+1,"Placa do personagem excede sala "+index);
  if(index<2)assert(at>=325,"Primeira fila deve estar próxima às cadeiras");
}
assert(source.includes("statusBar(c,x,y+(artMode==='pixellab'?54:62)"),"Rótulos compactos não aplicados");
console.log("ESTACOES_PIXELLAB_OK: oito cadeiras, placas dentro da sala e sem agentes nas janelas");

assert(source.includes("const symbols=['D','R','A','M','N','E','Q','P']"),
  "Faltam marcadores dos 8 cargos na arte PixelLab");
assert(source.includes("const map=window.VideoForgeOfficeMap"),
  "Os ambientes devem usar a mesma configuração do roteador");
console.log("ROLE_MARKERS_OK: identificação visual dos oito agentes");
