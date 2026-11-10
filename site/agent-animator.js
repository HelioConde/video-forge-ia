/* Atlas PixelLab: walk pode ter oito colunas; os outros movimentos têm quatro.
   Não consulta API nem usa tokens no navegador. */
(() => {
  "use strict";
  const ALLOWED=["idle","walk","type","sit","talk","wave"];
  const DIRECTIONS=["south","south-east","east","north-east",
                    "north","north-west","west","south-west"];
  const base="./assets/pixellab/agents/alex/";
  const images=new Map();
  let available=false,loading=null,baseManifest=null;
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
          const frames=motion==="walk"&&spec?.frames===8?8:4;
          const frameWidth=spec?.frameWidth||data.frameWidth;
          const frameHeight=spec?.frameHeight||data.frameHeight;
          if(!spec||!validPath(spec.file)||spec.file!==motion+".png"||
             !Number.isInteger(frameWidth)||!Number.isInteger(frameHeight)||
             frameWidth<16||frameWidth>128||frameHeight<16||frameHeight>128||
             spec.width!==frameWidth*frames||spec.height!==frameHeight*8){
            reject(new Error("Spritesheet inválida: "+motion));return;
          }
          const image=new Image();
          image.decoding="async";
          image.onload=()=>{
            if(image.naturalWidth!==frameWidth*frames||image.naturalHeight!==frameHeight*8){
              reject(new Error("Dimensões inválidas: "+motion));return;
            }
            resolve([motion,image]);
          };
          image.onerror=()=>reject(new Error("Atlas indisponível: "+motion));
          image.src=base+spec.file;
        })));
        for(const [motion,image] of assets)images.set(motion,image);
        baseManifest=data;
        available=true;
      }catch(error){
        available=false;
        baseManifest=null;
        images.clear();
        console.warn("VideoForge: sprites Alex indisponíveis, mantendo desenho original.",error.message);
      }
      return available;
    })();
    return loading;
  }
  function frameCount(motion){
    const spec=baseManifest?.motions?.[motion];
    return motion==="walk"&&spec?.frames===8?8:4;
  }
  function draw(ctx,motion,direction,frame,x,y,size=88){
    if(!available||!ALLOWED.includes(motion))return false;
    const dirIndex=DIRECTIONS.indexOf(direction);
    const atlas=images.get(motion);
    if(dirIndex<0||!atlas)return false;
    const offset=Math.floor(Math.max(0,Number(frame)||0))%frameCount(motion);
    const frameWidth=baseManifest?.motions?.[motion]?.frameWidth||88;
    const frameHeight=baseManifest?.motions?.[motion]?.frameHeight||88;
    const px=Math.round(x-size/2),py=Math.round(y-size/2);
    ctx.imageSmoothingEnabled=false;
    ctx.drawImage(atlas,offset*frameWidth,dirIndex*frameHeight,
                  frameWidth,frameHeight,px,py,size,size);
    return true;
  }
  // Atlas de novas animações: carregamento sob demanda, preservando os seis básicos.
  let productionManifest=null,productionLoading=null;
  const productionImages=new Map();
  async function loadProductionManifest(){
    if(productionLoading)return productionLoading;
    productionLoading=(async()=>{
      try{
        const response=await fetch(base+"production/manifest.json",{cache:"no-store"});
        if(!response.ok)return [];
        const manifest=await response.json();
        if(manifest.schema!=="videoforge/pixellab-production-atlas/v1"||
           manifest.character!=="alex"||manifest.frames!==4||
           manifest.frameWidth!==88||manifest.frameHeight!==88||
           typeof manifest.motions!=="object"||!manifest.motions)
           throw Error("Catálogo de sprites extras inválido");
        const entries=Object.entries(manifest.motions);
        if(entries.length>150)throw Error("Catálogo de sprites extras excede limite");
        for(const [motion,spec] of entries){
          if(!/^[a-z][a-z0-9_]{1,49}$/.test(motion)||
             !Array.isArray(spec.directions)||spec.directions.length<1||
             spec.directions.length>8||!spec.directions.every(x=>DIRECTIONS.includes(x))||
             spec.file!==motion+".png"||spec.width!==352||
             spec.height!==88*spec.directions.length)
             throw Error("Entrada de sprite extra inválida");
        }
        productionManifest=manifest;
        return entries.map(([name,spec])=>({name,category:spec.category}));
      }catch(e){
        console.warn("VideoForge: animações extras indisponíveis.",e.message);
        return [];
      }
    })();
    return productionLoading;
  }
  function productionMotions(){
    return productionManifest?
      Object.entries(productionManifest.motions).map(([name,spec])=>({name,category:spec.category})):[];
  }
  function productionLoaded(motion){return productionImages.has(motion);}
  async function preloadProduction(motion){
    if(!productionManifest)await loadProductionManifest();
    const spec=productionManifest?.motions?.[motion];
    if(!spec)return false;
    if(productionImages.has(motion))return true;
    try{
      const image=await new Promise((resolve,reject)=>{
        const sprite=new Image();
        sprite.decoding="async";
        sprite.onload=()=>resolve(sprite);
        sprite.onerror=()=>reject(Error("Sprite não carregou"));
        sprite.src=base+"production/"+spec.file;
      });
      if(image.naturalWidth!==spec.width||image.naturalHeight!==spec.height)return false;
      productionImages.set(motion,image);
      return true;
    }catch(e){return false;}
  }
  function drawProduction(ctx,motion,direction,frame,x,y,size=88){
    const image=productionImages.get(motion);
    const spec=productionManifest?.motions?.[motion];
    if(!image||!spec)return false;
    // Só para prévia: se não houver o ângulo da mesa, mostrar um quadro válido.
    // O status real do agente nunca é deduzido da animação.
    const selected=spec.directions.includes(direction)?direction:spec.directions[0];
    const row=spec.directions.indexOf(selected);
    if(row<0)return false;
    const col=Math.floor(Math.max(0,Number(frame)||0))%4;
    ctx.imageSmoothingEnabled=false;
    ctx.drawImage(image,col*88,row*88,88,88,Math.round(x-size/2),Math.round(y-size/2),size,size);
    return true;
  }
  window.VideoForgeAnimator={
    preload,ready:()=>available,draw,frameCount,motions:ALLOWED.slice(),
    loadProductionManifest,productionMotions,preloadProduction,productionLoaded,drawProduction
  };
})();
