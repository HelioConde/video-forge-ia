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


// Independent status telemetry covers stages where the Checks API fails.
const statusEditor=(id,state="pending",ctx="VideoForge Stage / autoeditor / otaku-br / editor")=>({
  id, sha:SHA, context:ctx, state,
  target_url:"https://github.com/HelioConde/video-forge-ia/actions/runs/43147397260",
});
const statusArtist=statusEditor(222,"pending","VideoForge Stage / autoeditor / otaku-br / artista");
const statusFallback=live.readEvidence(RUN,[],[statusArtist,statusEditor(223)]);
assert.equal(statusFallback.tasks.length,2);
assert.equal(statusFallback.tasks.find(x=>x.role==="editor").status,"in_progress");
assert.equal(statusFallback.tasks.find(x=>x.role==="artista").origin,"github_commit_status");
const withEditor={...snapshot,agentes:[...snapshot.agentes,
  {id:"editor",status:"nao_conectado",canal:null}]};
const mergedFallback=live.merge(withEditor,statusFallback);
assert.equal(mergedFallback.agentes.find(x=>x.id==="editor").status,"trabalhando");
assert.equal(mergedFallback.agentes.find(x=>x.id==="editor").execucao_pipeline.origem,"github_commit_status");
assert.equal(mergedFallback.agentes.find(x=>x.id==="publicador").status,"nao_conectado");

// Completion stops the editor; an old pending status cannot imply live work.
const stageDone=live.readEvidence({...RUN,status:"completed",conclusion:"success"},[],
  [statusEditor(226,"success")]);
assert.equal(live.merge(withEditor,stageDone).agentes.find(x=>x.id==="editor").status,
  "concluido");
const stageOld=live.readEvidence({...RUN,status:"completed",conclusion:"failure"},[],
  [statusEditor(225,"pending")]);
assert.notEqual(live.merge(withEditor,stageOld).agentes.find(x=>x.id==="editor").status,
  "trabalhando");

// Invalid source, forged URLs, attempted publication and wrong commit are ignored.
for(const corrupt of [
  {...statusEditor(301),sha:"b".repeat(40)},
  {...statusEditor(302),target_url:"https://evil.example/work"},
  statusEditor(303,"pending","VideoForge Stage / autoeditor / otaku-br / publicador"),
  statusEditor(304,"pending","VideoForge Stage / autoeditor / other-channel / editor"),
  {...statusEditor(305),state:"unknown"},
]) {
  const rows=live.readEvidence(RUN,[],[corrupt]).tasks;
  // Unknown channels are filtered when merging, not inside the parser.
  if(corrupt.context.includes("other-channel")) {
    assert.equal(live.merge(withEditor,live.readEvidence(RUN,[],[corrupt]))
      .agentes.find(x=>x.id==="editor").status,"nao_conectado");
  } else {
    assert.equal(rows.length,0);
  }
}
const checkPending=live.readEvidence(RUN,[PROOF("narrador")],
  [statusEditor(331,"success","VideoForge Stage / autoeditor / otaku-br / narrador")]);
assert.equal(checkPending.tasks[0].status,"completed");
assert.equal(checkPending.tasks[0].conclusion,"success");

let count=0;
async function fakeFetch(url){
  count++;
  const result=url.includes("/actions/workflows/")?
    {workflow_runs:[RUN]}:url.includes("/check-runs")?
    {check_runs:[PROOF("narrador")]}:
    [statusEditor(330,"success","VideoForge Stage / autoeditor / otaku-br / editor")];
  return {ok:true,json:async()=>result};
}
(async()=>{
  const loaded=await live.load(fakeFetch);
  assert.equal(count,3);
  assert.equal(loaded.tasks.length,2);
  assert.equal(loaded.url,"https://github.com/HelioConde/video-forge-ia/actions/runs/43147397260");
  const absentChecks=await live.load(async url=>({
    ok:!url.includes("check-runs"),
    json:async()=>url.includes("workflow_runs")?{workflow_runs:[RUN]}:
      url.includes("/actions/workflows/")?{workflow_runs:[RUN]}:
      [statusEditor(336)]
  }));
  assert.equal(absentChecks.tasks.length,1);
  assert.equal(absentChecks.tasks[0].role,"editor");
  console.log("Office live evidence tests passed");
})().catch(err=>{console.error(err);process.exitCode=1;});
