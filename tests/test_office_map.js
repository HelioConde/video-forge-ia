"use strict";
const assert=require("node:assert/strict");
global.window={};
require("../site/office-map.js");
const map=window.VideoForgeOfficeMap;
const rooms=Object.values(map.rooms);
assert.equal(rooms.length,6,"Três salas aprovadas + três ambientes de prévia");
assert.equal(rooms.filter(x=>x.status==="preview").length,3);
for(const [id,dest] of Object.entries(map.destinations)){
  assert(map.rooms[dest.room],"Destino sem sala: "+id);
  const room=map.rooms[dest.room];
  assert(dest.x>room.x+20&&dest.x<room.x+room.w-20,"Destino fora da sala x: "+id);
  assert(dest.y>room.y+35&&dest.y<room.y+room.h-15,"Destino fora da sala y: "+id);
}
assert.equal(map.stations.length,9);
assert.equal(map.stations.filter(p=>p.standing).length,1);
assert.equal(map.stations.at(-1).id,'subgerente');
assert.equal(new Set(map.stations.map(p=>p.room)).size,3);
assert.equal(map.meetings.length,2);
assert.notEqual(map.meetings[0].x,map.meetings[1].x);
console.log("OFFICE_MAP_OK: rotas e destinos correspondem às salas do cenário");