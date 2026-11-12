// Test the actual TypeScript shipped to Remotion, not a JS approximation.
// Run from the checked-out AutoEditorVideo/motion-remotion after npm ci.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require(path.join(process.cwd(),'node_modules','typescript'));
const location=path.join(process.cwd(),'src','videoforge-motion.ts');
const original=fs.readFileSync(location,'utf8');
const compiled=ts.transpileModule(original,{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020
}}).outputText;
const mod={exports:{}};
new Function('module','exports',compiled)(mod,mod.exports);
const animate=mod.exports.videoForgeMotionAtFrame;
const sample=(motion,id='gota',distance=36,start=0,end=1)=>({
  id,motion,distance,start,end
});
const scene=(cues,frame)=>animate(cues,frame,0,150);
const start=scene([sample('hop','fofinho')],0);
const peak=scene([sample('hop','fofinho')],75);
const end=scene([sample('hop','fofinho')],150);
assert.equal(start.opacity,1);
assert.equal(end.opacity,1);
assert.match(start.transform,/translate\(0px,0px\)/);
assert.match(end.transform,/translate\(0px,0px\)/);
assert.notEqual(peak.transform,end.transform);
const rise=scene([sample('rise','gotinha',27,.15,.45)],70);
const fall=scene([
  sample('rise','gotinha',27,.15,.45),
  sample('fall','gotinha',27,.5,.85)
],132);
assert.notEqual(rise.transform,fall.transform);
const paw=scene([sample('paw-wave','patinha',26,.15,.85)],58);
assert.match(paw.transform,/rotate\((-|\d)/);
const float=scene([sample('float')],82);
assert.notEqual(float.transform,start.transform);
const boom=scene([sample('pop')],0);
assert.equal(boom.opacity,0);
assert.equal(scene([sample('pop')],149).opacity,1);
for(const cue of ['hop','idle','rise','fall','paw-lift','paw-wave','pat','walk',
                   'approach','bounce','float','orbit','pulse','sway','snuggle',
                   'settle','pop']){
  for(const frame of [0,15,45,75,100,149,150]){
    const res=scene([sample(cue)],frame);
    assert.ok(!res.transform.includes('NaN'),cue);
    assert.ok(!res.transform.includes('Infinity'),cue);
    assert.ok(res.opacity>=0 && res.opacity<=1);
    assert.equal(res,undefined, false);
    assert.deepEqual(scene([sample(cue)],frame),res,'determinism: '+cue);
  }
}
assert.ok(!original.includes('Math.random('));
assert.ok(!original.includes('Date.now('));
console.log('Fofinho sprite-motion TS: frame tests passed');
