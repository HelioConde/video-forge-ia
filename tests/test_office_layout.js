/* Postos por setor, rótulos íntegros e sem duplicar agentes. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
global.window={};
require("../site/office-map.js");
const map=window.VideoForgeOfficeMap;
const source=fs.readFileSync("site/office-art.js","utf8");
assert(source.includes("const pixelStations=window.VideoForgeOfficeMap.stations.map"));
const ids=["diretor","roteirista","artista","animador","narrador",
           "editor","revisor","publicador"];
assert.deepEqual(map.stations.map(p=>p.id),ids);
assert.equal(map.stations.length,8);
assert.equal(new Set(map.stations.map(p=>p.x+","+p.y)).size,8);
const expected={diretor:"production",roteirista:"production",
  artista:"creative",animador:"creative",narrador:"media",editor:"media",
  revisor:"production",publicador:"production"};
for(const item of map.stations){
  assert.equal(item.room,expected[item.id]);
  const r=map.rooms[item.room],x=item.x,y=item.y+111;
  assert(x>=r.x+58&&x<=r.x+r.w-58,"Placa lateral sai da sala: "+item.id);
  assert(y-36>=r.y+75,"Agente sobre a parede: "+item.id);
  assert(y+67<r.y+r.h-5,"Rótulo para fora da sala: "+item.id);
}
assert(source.includes("const labelOffset=artMode==='pixellab'?window.VideoForgeOfficeMap.character.labelOffset:62;"));
assert(source.includes("statusBar(c,x,y+labelOffset"));
assert.equal(map.character.seatedSize,88);
assert.equal(map.character.standingSize,84);
assert.equal(map.character.labelOffset,60);
assert.equal(map.seat.dy,0,"As cadeiras devem ficar alinhadas à mesa PixelLab");
assert(source.includes("const symbols=['D','R','A','M','N','E','Q','P']"));
console.log("OFFICE_ROLES_OK: 4 na Produção, 2 na Criação, 2 no Laboratório");

// Contrato visual: as imagens completas de salas permanecem como assets,
// mas não podem mais dividir a agência em construções separadas.
assert(source.includes("paintBackground:c=>pixelBase(c)"));
assert(source.includes("const classicStations=window.VideoForgeOfficeMap.stations.map"));
assert(source.includes("UMA EQUIPE"));
assert(source.includes("areaRug(86,274,501,418"));
assert(!source.includes("sprite(c,'main',79,194,512,512)"));
assert(!source.includes("floorRoom('breakroom'"));
console.log("LAYOUT_UNIFICADO_OK: cenário e avatares compartilham o mesmo andar");
