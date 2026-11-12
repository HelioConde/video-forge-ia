/** VideoForge character/prop sprite choreography.
 * Pure deterministic per-frame math inspired by Fofinho EP01 Part 3.
 * Works only with actual extracted RGBA layers, not fake limb articulation.
 * No remote calls, no random, no timers, no imaginary 3D rig.
 */
export type VideoForgeMotionCue={
  id:string;motion:string;start:number;end:number;distance:number;
};
export type VideoForgeMotionTransform={transform:string;opacity:number};
const clamp=(x:number,a=0,b=1)=>Math.min(b,Math.max(a,x));
const ease=(t:number)=>{const p=clamp(t);return p*p*(3-2*p);};
const round=(x:number)=>Number(x.toFixed(3));

export const videoForgeMotionAtFrame=(
  cues:VideoForgeMotionCue[],frame:number,sceneStart:number,sceneEnd:number
):VideoForgeMotionTransform=>{
  if(!cues?.length||!Number.isFinite(frame)||sceneEnd<=sceneStart)
    return {transform:'translate(0px,0px) rotate(0deg) scale(1)',opacity:1};
  const elapsed=clamp((frame-sceneStart)/(sceneEnd-sceneStart));
  let dx=0,dy=0,rotation=0,scale=1,opacity=1;
  for(const cue of cues){
    if(!Number.isFinite(cue.start)||!Number.isFinite(cue.end)||
       !Number.isFinite(cue.distance)||cue.end<=cue.start)continue;
    const amplitude=clamp(cue.distance,0,46);
    const progress=clamp((elapsed-cue.start)/(cue.end-cue.start));
    const ongoing=elapsed>=cue.start&&elapsed<=cue.end;
    const p=ease(progress);
    const bump=Math.sin(Math.PI*p);
    switch(cue.motion){
      // Movement through scene time; finishing position is held after cue.
      case 'walk':case 'approach':
        dx+=amplitude*p;
        dy+=ongoing?Math.sin(progress*Math.PI*7)*Math.min(amplitude*.12,4)*bump:0;
        break;
      case 'rise': dy-=amplitude*p; break;
      case 'fall': case 'drop': dy+=amplitude*p;break;
      case 'settle':dy+=amplitude*p;break;
      case 'snuggle':dx+=amplitude*.35*p;dy-=amplitude*.10*p;break;
      case 'paw-lift':
        dy-=amplitude*.45*p;
        rotation-=Math.min(18,amplitude*.6)*p;
        break;
      case 'pop':
        opacity*=clamp(progress*3);
        scale*=1+.06*bump; break;
      // Nonpersistent motions return to original placement at cue end.
      case 'hop':dy-=amplitude*bump;break;
      case 'bounce':dy-=amplitude*.8*Math.abs(Math.sin(3*Math.PI*progress))*bump;break;
      case 'float':
        if(ongoing)dy-=amplitude*.36*Math.sin(progress*6*Math.PI)*bump;
        break;
      case 'orbit':
        if(ongoing){
          dx+=amplitude*.6*Math.sin(progress*2*Math.PI)*bump;
          dy-=amplitude*.35*(1-Math.cos(progress*2*Math.PI))*bump;
        }
        break;
      case 'paw-wave':
        if(ongoing)rotation+=Math.min(22,amplitude*.68)*
          Math.sin(progress*Math.PI*4)*bump;
        break;
      case 'pat':
        if(ongoing){dy+=amplitude*.23*Math.sin(progress*2*Math.PI)*bump;}
        break;
      case 'sway':
        if(ongoing)rotation+=Math.min(10,amplitude*.25)*
          Math.sin(progress*Math.PI*3)*bump;
        break;
      case 'pulse':
        if(ongoing)scale*=1+.035*bump;break;
      case 'idle':
        if(ongoing)dy-=Math.min(4,amplitude*.12)*
          Math.sin(progress*4*Math.PI)*bump;
        break;
      case 'still':break;
      default:break;
    }
  }
  // Only rigid 2D motion, identical scaling in both axes.
  return {transform:'translate('+round(dx)+'px,'+round(dy)+
    'px) rotate('+round(rotation)+'deg) scale('+round(scale)+')',
    opacity:round(clamp(opacity))};
};
