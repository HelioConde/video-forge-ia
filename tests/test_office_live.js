"use strict";
const assert = require("node:assert/strict");
const live = require("../site/office-live.js");
const SHA = "a".repeat(40);
const RUN = {
  id: 43147397260, head_sha: SHA, status: "in_progress", event: "push",
  conclusion: null, updated_at: "2026-11-12T03:20:00Z"
};
const PROOF = (role, status="in_progress", conclusion=null, id=100) => ({
  id, name: live.PREFIX + role, status, conclusion, head_sha: SHA,
  external_id: "vf-autoeditor:43147397260:otaku-br:" + role,
  details_url: "https://github.com/HelioConde/video-forge-ia/actions/runs/43147397260",
});
const snapshot = {
  schema:"videoforge/agent-office/v1", fonte:"apenas_configuracao",
  canais:[{id:"otaku-br",nome:"Otaku Multicena"}],
  agentes:[
    {id:"narrador",status:"nao_conectado",canal:null,
     conexao:{modelo_definido:false,executor_habilitado:false,eventos_observados:false,
     pendencias:["Sem telemetria de execução comprovada"]}},
    {id:"artista",status:"nao_conectado",canal:null},
    {id:"publicador",status:"nao_conectado",canal:null},
    {id:"subgerente",status:"nao_conectado",canal:null}
  ]
};

let record = live.readEvidence(RUN, [PROOF("narrador")]);
assert.equal(record.tasks.length, 1);
let merged = live.merge(snapshot, record);
assert.equal(merged.agentes[0].status, "trabalhando");
assert.equal(merged.agentes[0].conexao.modelo_definido, false);
assert.equal(merged.agentes[0].conexao.executor_habilitado, false);
assert.equal(merged.agentes[1].status, "nao_conectado");
assert.equal(merged.agentes[2].status, "nao_conectado");
assert.equal(merged.agentes[3].status, "nao_conectado");
assert.equal(merged.tempo_real, false);
assert.equal(snapshot.agentes[0].status, "nao_conectado");

record = live.readEvidence({...RUN,status:"completed",conclusion:"success"},[PROOF("narrador")]);
merged = live.merge(snapshot,record);
assert.notEqual(merged.agentes[0].status,"trabalhando","closed runs never imply live work");
assert.equal(merged.agentes[0].status,"erro","unfinished role must not appear completed");

record = live.readEvidence({...RUN,status:"completed",conclusion:"success"},[
  PROOF("narrador","completed","success")]);
merged = live.merge(snapshot,record);
assert.equal(merged.agentes[0].status,"concluido");
assert.equal(merged.agentes[2].status,"nao_conectado");

record = live.readEvidence({...RUN,status:"completed",conclusion:"failure"},[
  PROOF("artista","completed","failure")]);
merged = live.merge(snapshot,record);
assert.equal(merged.agentes[1].status,"erro");

const rejected = [
  {...PROOF("narrador"), external_id:"vf-autoeditor:999:otaku-br:narrador"},
  {...PROOF("narrador"), details_url:"https://evil.example"},
  {...PROOF("narrador"), head_sha:"b".repeat(40)},
  {...PROOF("publicador"), external_id:"vf-autoeditor:43147397260:otaku-br:publicador"},
  {...PROOF("narrador"), external_id:"vf-autoeditor:43147397260:../secrets:narrador"},
];
assert.equal(live.readEvidence(RUN,rejected).tasks.length,0);

// Editorial research has different evidence and does NOT activate media workers.
const editorialProof = {
  id:220,
  name:live.PREFIX+"subgerente",
  status:"completed", conclusion:"success",
  head_sha:SHA, external_id:"vf-editorial:43147397260:otaku-br:subgerente",
  details_url:"https://github.com/HelioConde/video-forge-ia/actions/runs/43147397260"
};
let editorial = live.readEvidence({...RUN,status:"completed"},[editorialProof]);
assert.equal(editorial.tasks.length,1);
assert.equal(editorial.tasks[0].kind,"editorial");
const extended = {...snapshot,agentes:[
  ...snapshot.agentes.filter(x=>x.id!=="subgerente"),
  {id:"subgerente",status:"nao_conectado",canal:null}
]};
let mergedEditorial = live.merge(extended,editorial);
assert.equal(mergedEditorial.agentes.find(x=>x.id==="subgerente").status,"concluido");
assert.match(mergedEditorial.agentes.find(x=>x.id==="subgerente").tarefa,/auditar/i);
assert.equal(mergedEditorial.agentes.find(x=>x.id==="publicador").status,"nao_conectado");

let count=0;
async function fakeFetch(url){
  count++;
  return {ok:true,json:async()=>count===1?
    {workflow_runs:[RUN]}:
    {check_runs:[PROOF("narrador")]}};
}
(async()=>{
  const loaded=await live.load(fakeFetch);
  assert.equal(count,2);
  assert.equal(loaded.tasks.length,1);
  assert.equal(loaded.url,"https://github.com/HelioConde/video-forge-ia/actions/runs/43147397260");
  console.log("Office live evidence tests passed");
})().catch(err=>{console.error(err);process.exitCode=1;});
