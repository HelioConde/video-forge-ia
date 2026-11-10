/* Atlas estático PixelLab: quatro colunas de frames e oito linhas de direções.
   Não consulta API nem usa tokens no navegador. */
(() => {
  "use strict";
  const ALLOWED=["idle","walk","type","sit","talk","wave"];
  const DIRECTIONS=["south","south-east","east","north-east",
                    "north","north-west","west","south-west"];
  const base="./assets/pixellab/agents/alex/";
  const images=new Map();
  let available=false,loading=null;
  const validPath=path=>/^[a-z]+\.png$/.test(path);
  async function preload(){
    if(loading)return loading;
    loading=(async()=>{
      try{
        const response=await fetch(base+"manifest.json",{cache:"no-store"});
        if(!response.ok)throw new Error("Manifest de animações indisponível");
        const data=await response.json();
        if(data.schema!=="videoforge/pixellab-agent-atlas/v1"||
           data.character!=="alex"||data.frames!==4||
           data.frameWidth!==88||data.frameHeight!==88||
           JSON.stringify(data.directions)!==JSON.stringify(DIRECTIONS))
           throw new Error("Manifest de animações incompatível");
        const assets=await Promise.all(ALLOWED.map(motion=>new Promise((resolve,reject)=>{
          const spec=data.motions?.[motion];
          if(!spec||!validPath(spec.file)||spec.file!==motion+".png"||
             spec.width!==352||spec.height!==704){
            reject(new Error("Spritesheet inválida: "+motion));return;
          }
          const image=new Image();
          image.decoding="async";
          image.onload=()=>{
            if(image.naturalWidth!==352||image.naturalHeight!==704){
              reject(new Error("Dimensões inválidas: "+motion));return;
            }
            resolve([motion,image]);
          };
          image.onerror=()=>reject(new Error("Atlas indisponível: "+motion));
          image.src=base+spec.file;
        })));
        for(const [motion,image] of assets)images.set(motion,image);
        available=true;
      }catch(error){
        available=false;
        images.clear();
        console.warn("VideoForge: sprites Alex indisponíveis, mantendo desenho original.",error.message);
      }
      return available;
    })();
    return loading;
  }
  function draw(ctx,motion,direction,frame,x,y,size=88){
    if(!available||!ALLOWED.includes(motion))return false;
    const dirIndex=DIRECTIONS.indexOf(direction);
    const atlas=images.get(motion);
    if(dirIndex<0||!atlas)return false;
    const offset=Math.floor(Math.max(0,Number(frame)||0))%4;
    const px=Math.round(x-size/2),py=Math.round(y-size/2);
    ctx.imageSmoothingEnabled=false;
    ctx.drawImage(atlas,offset*88,dirIndex*88,88,88,px,py,size,size);
    return true;
  }
  window.VideoForgeAnimator={preload,ready:()=>available,draw,motions:ALLOWED.slice()};
})();
