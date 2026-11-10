/* VIDEOFORGE AI — handmade pixel-art scene. Original artwork. */
const SW=1280, SH=820;
const classicStations=[[174,295],[346,295],[518,295],[690,295],[174,528],[346,528],[518,528],[690,528]];
const pixelStations=[[205,143],[456,143],[205,253],[456,253],[205,363],[456,363],[205,473],[456,473]];
// A matriz é mantida por referência; o renderizador e o hit-test usam os mesmos slots.
const stations=classicStations.map(p=>p.slice());
let artMode='classic',spritesReady=false;
const spriteImages={};
const SPRITE_PATHS={
  main:'scenes/main-office.png',
  creative:'scenes/creative-room.png',
  media:'scenes/media-lab.png',
  desk:'objects/desk-pc.png',
  chair:'objects/office-chair.png',
  plant:'objects/plant.png',
  bookshelf:'objects/bookshelf.png',
  audio:'objects/audio-mixer.png',
  editing:'objects/studio-screen.png'
};
function loadSprites(){
  const names=Object.entries(SPRITE_PATHS);
  return Promise.all(names.map(([key,path])=>new Promise((resolve,reject)=>{
    const img=new Image();
    img.decoding='async';
    img.onload=()=>{if(!img.naturalWidth||!img.naturalHeight)reject(new Error('Sprite inválido: '+key));
                 else resolve([key,img]);};
    img.onerror=()=>reject(new Error('Sprite ausente: '+key));
    img.src='./assets/pixellab/'+path;
  }))).then(results=>{
    results.forEach(([key,img])=>spriteImages[key]=img);
    spritesReady=true;return true;
  }).catch(err=>{console.warn('PixelLab: mantendo arte original.',err.message);return false;});
}
function setArtMode(mode){
  if(!['classic','pixellab'].includes(mode))return false;
  if(mode==='pixellab'&&!spritesReady)return false;
  artMode=mode;
  const target=mode==='pixellab'?pixelStations:classicStations;
  target.forEach((slot,i)=>{stations[i][0]=slot[0];stations[i][1]=slot[1];});
  return true;
}
function sprite(c,key,x,y,w,h){
  const img=spriteImages[key];
  if(img)c.drawImage(img,Math.round(x),Math.round(y),Math.round(w),Math.round(h));
}
function pixelBase(c){
  rect(c,0,0,SW,SH,'#152331');
  for(let y=0;y<SH;y+=32)for(let x=0;x<SW;x+=32)
    if((x/32+y/32)%2===0)rect(c,x,y,32,32,'#192c3a');
  rect(c,25,113,1226,675,'#233747');
  line(c,25,113,1226,675,'#587380',4);
  rect(c,45,137,1183,35,'#122434');
  text(c,'PIXEL STUDIO  /  VIDEOFORGE AI',66,160,'#b9e6d1',15);
  text(c,'3 SALAS   +   6 OBJETOS',1200,159,'#d6c79d',12,'right');
  // As cenas PixelLab são top-down: preservar a proporção nativa e pixels nítidos.
  sprite(c,'main',79,194,512,512);
  sprite(c,'creative',655,196,256,256);
  sprite(c,'media',954,196,256,256);
  text(c,'PRODUÇÃO',337,190,'#e7dbc5',15,'center');
  text(c,'SALA CRIATIVA',783,190,'#e7dbc5',13,'center');
  text(c,'LABORATÓRIO',1082,190,'#e7dbc5',13,'center');
  rect(c,631,479,595,267,'#253b49');
  line(c,631,479,595,267,'#678383',3);
  text(c,'OBJETOS / MOBILIÁRIO',651,503,'#bce6d0',14);
  // Sprites transparentes, reutilizáveis e sem fundo pintado por cima do cenário.
  sprite(c,'desk',650,519,128,128);
  sprite(c,'chair',793,549,84,84);
  sprite(c,'plant',898,539,86,86);
  sprite(c,'bookshelf',1001,513,124,124);
  sprite(c,'audio',720,637,118,100);
  sprite(c,'editing',920,638,128,101);
  text(c,'DESK',713,661,'#d0d9cc',10,'center');
  text(c,'CHAIR',831,658,'#d0d9cc',10,'center');
  text(c,'PLANT',940,658,'#d0d9cc',10,'center');
  text(c,'SHELF',1060,658,'#d0d9cc',10,'center');
  text(c,'AUDIO',774,748,'#d0d9cc',10,'center');
  text(c,'EDITING',984,754,'#d0d9cc',10,'center');
}
function rect(c,x,y,w,h,col){c.fillStyle=col;c.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
function line(c,x,y,w,h,col,t=2){c.lineWidth=t;c.strokeStyle=col;c.strokeRect(Math.round(x)+.5,Math.round(y)+.5,w,h);}
function text(c,s,x,y,col='#f2e7d6',size=12,align='left'){c.fillStyle=col;c.textAlign=align;c.textBaseline='alphabetic';c.font='bold '+size+'px monospace';c.fillText(s,x,y);}
function noise(x,y){return ((x*73856093^y*19349663)>>>0)%97;}
function ellipse(c,x,y,rx,ry,col){c.fillStyle=col;c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fill();}
function star(c,x,y,clr='#fff0ba'){rect(c,x-1,y-5,2,12,clr);rect(c,x-5,y-1,10,2,clr);}
function plant(c,x,y,s=1){c.save();c.translate(x,y);c.scale(s,s);ellipse(c,1,17,23,8,'#1d3037');rect(c,-15,0,30,20,'#6f4d47');rect(c,-12,-3,24,8,'#ba8b64');rect(c,-4,-12,8,19,'#3b5944');[[0,-40,23,17,'#5b9970'],[-17,-28,13,20,'#4c9065'],[17,-30,14,19,'#7bb989'],[-7,-53,14,18,'#8ac598']].forEach(a=>{ellipse(c,a[0],a[1],a[2]/2,a[3],a[4]);});rect(c,-3,-53,5,10,'#b2d1a0');c.restore();}
function windowScene(c,x,y){rect(c,x,y,138,80,'#172c3b');rect(c,x+7,y+6,124,61,'#86bdc3');rect(c,x+7,y+6,124,30,'#c3e5db');rect(c,x+7,y+37,124,30,'#94b6b1');rect(c,x+8,y+50,124,17,'#6b9c91');rect(c,x+14,y+24,22,26,'#84a59c');rect(c,x+38,y+19,16,31,'#9dc1b4');rect(c,x+83,y+32,27,17,'#6f9e98');rect(c,x+66,y+8,8,60,'#253b48');rect(c,x+7,y+36,124,7,'#253b48');rect(c,x-3,y+65,144,12,'#c89b7c');rect(c,x-3,y+74,144,4,'#845c52');}
function clock(c,x,y){ellipse(c,x,y+2,24,24,'#253443');ellipse(c,x,y,19,19,'#e4d4ad');ellipse(c,x,y,13,13,'#f3ebd4');rect(c,x-1,y-13,2,14,'#455a62');rect(c,x-1,y-1,12,2,'#455a62');rect(c,x-2,y-2,4,4,'#455a62');}
function shelf(c,x,y,w=95){rect(c,x-7,y-6,w+13,79,'#233645');rect(c,x,y,w,65,'#9e735c');for(let k=0;k<2;k++){rect(c,x+4,y+29*k+25,w-9,5,'#5d4649');for(let i=0;i<Math.floor((w-13)/10);i++){const palette=['#c88986','#a9c3b0','#e1c18f','#759fac','#bca4c9'];rect(c,x+8+i*10,y+3+k*29+(i%3)*2,7,21-(i%3)*2,palette[(i+k*2)%5]);}}rect(c,x-8,y+66,w+16,7,'#493947');}
function wall(c){rect(c,10,10,1260,800,'#0c1a2b');rect(c,29,26,1222,763,'#3d5062');rect(c,40,38,1199,741,'#b88564');rect(c,49,48,1180,705,'#a87855');rect(c,49,48,1180,100,'#3b5668');for(let x=49;x<1230;x+=36)rect(c,x,53,2,88,'#486a78');rect(c,49,138,1180,14,'#223949');rect(c,49,151,1180,12,'#a2795f');windowScene(c,115,59);windowScene(c,303,59);windowScene(c,490,59);windowScene(c,676,59);shelf(c,55,61,42);clock(c,860,102);rect(c,925,66,275,61,'#1f3746');line(c,925,66,275,61,'#82b0ae',5);rect(c,938,77,249,39,'#25495a');text(c,'VIDEOFORGE',1062,106,'#b9ffe0',28,'center');rect(c,940,114,244,4,'#65cbb1');rect(c,49,742,1180,13,'#3c3a3e');rect(c,49,755,1180,10,'#c39b75');rect(c,30,26,19,764,'#152838');rect(c,1230,26,20,764,'#172838');rect(c,29,25,1223,18,'#14283c');rect(c,29,779,1223,14,'#152838');line(c,34,32,1210,754,'#677a88',3);}
function floor(c){rect(c,49,162,1180,580,'#af845f');for(let y=162;y<743;y+=24){rect(c,49,y,1180,2,y%48?'#a47858':'#d1a075');for(let x=49+(((y/24)|0)%2)*68;x<1225;x+=136){rect(c,x,y,2,22,'#815f50');if(noise(x,y)%5===0)rect(c,x+44,y+14,35,2,'#c79a75');}}for(let i=0;i<5;i++){const xx=128+i*188;rect(c,xx,165,110,168,'#efc59c25');rect(c,xx+10,164,12,147,'#f6d6aa20');}for(let y=200;y<705;y+=70)for(let x=83;x<1180;x+=80)if(noise(x,y)%11===0)rect(c,x,y,4,3,'#e8b18b');}
function divider(c){rect(c,819,162,12,580,'#203746');rect(c,829,162,7,580,'#5b6d75');rect(c,819,440,17,70,'#b38a66');rect(c,832,443,4,63,'#f3ce8f');}
function meeting(c){rect(c,840,169,373,265,'#516b78');rect(c,849,179,354,244,'#3b5966');for(let y=180;y<423;y+=45)rect(c,849,y,354,2,'#617b83');rect(c,855,213,335,192,'#6a8490');rect(c,863,221,319,176,'#91a49d');rect(c,869,228,307,163,'#486879');rect(c,868,235,304,9,'#b6c7b2');rect(c,873,251,291,130,'#3e6678');rect(c,893,261,247,81,'#294559');rect(c,898,266,237,73,'#547888');text(c,'CREATIVE  ROOM',1018,282,'#b4e4d0',16,'center');rect(c,916,302,64,21,'#8ec9b6');rect(c,990,302,60,21,'#eac18d');rect(c,1061,302,60,21,'#8eb7cd');ellipse(c,1015,353,137,31,'#28485b');rect(c,934,347,172,40,'#b78c65');rect(c,935,343,170,17,'#d7ab7b');rect(c,947,359,8,28,'#7a5e4f');rect(c,1085,359,8,28,'#7a5e4f');for(const x of [947,1083]){rect(c,x,309,38,32,'#567183');rect(c,x+7,321,26,12,'#819eab');}plant(c,867,241,.8);plant(c,1173,395,.85);}
function studio(c){rect(c,840,481,371,248,'#334952');rect(c,850,490,352,227,'#466575');for(let x=860;x<1189;x+=43)rect(c,x,499,2,199,'#517485');rect(c,864,509,320,183,'#1e3447');rect(c,871,516,306,169,'#2f4b5a');rect(c,884,530,130,106,'#152638');rect(c,890,535,118,84,'#537688');rect(c,894,541,110,22,'#27485f');rect(c,903,550,93,4,'#9be9bd');for(let i=0;i<5;i++)rect(c,900+i*19,578+((i%2)*12),11,35-(i%2)*12,['#a3d4c7','#d0b48b','#7dacb6'][i%3]);rect(c,1040,537,118,87,'#152638');rect(c,1048,546,101,63,'#22495e');for(let j=0;j<6;j++)rect(c,1057+j*14,561+(j%3)*10,7,31-(j%3)*10,['#79c6a8','#c89d81','#a6c5ce'][j%3]);rect(c,875,642,301,15,'#9c785d');rect(c,883,657,287,13,'#5d504d');rect(c,894,675,17,10,'#7f8d8e');rect(c,1153,675,17,10,'#7f8d8e');plant(c,863,692,.7);rect(c,855,451,348,27,'#203b4a');text(c,'MEDIA LAB   /   RENDER + AUDIO',1028,469,'#d1e2ce',13,'center');}
function carpet(c,x,y,w,h){ellipse(c,x+w/2,y+h-7,w*.54,15,'#584f4b');rect(c,x+4,y+5,w-8,h-16,'#78645c');rect(c,x,y,w,h-20,'#8f7771');rect(c,x+7,y+8,w-14,h-37,'#ab9282');line(c,x+8,y+8,w-16,h-37,'#d4b397',3);for(let k=0;k<5;k++){rect(c,x+18+k*(w-37)/5,y+18,2,h-60,'#bba28b');}}
function desk(c,x,y,i){ellipse(c,x,y+65,77,18,'#5d4e44');rect(c,x-61,y-19,128,70,'#664942');rect(c,x-67,y-31,137,70,'#9c6c56');rect(c,x-63,y-29,128,56,'#ce9b74');rect(c,x-57,y-22,116,5,'#e7b98a');rect(c,x-57,y+29,116,6,'#93644f');rect(c,x-62,y+37,12,21,'#674847');rect(c,x+50,y+37,13,21,'#674847');rect(c,x-31,y+7,42,4,'#7e6255');rect(c,x-27,y-5,39,24,'#27394b');rect(c,x-22,y-1,30,17,i%2?'#2d6476':'#2d5b60');rect(c,x-19,y+3,12,2,'#a6e4bc');rect(c,x-19,y+8,21,2,'#8bbbc4');rect(c,x-17,y+12,8,2,'#7aa0a9');rect(c,x-10,y+19,7,5,'#2a4650');rect(c,x-31,y+24,48,4,'#435365');rect(c,x+18,y+12,28,9,'#d0c3a1');for(let k=0;k<4;k++)rect(c,x+21+k*5,y+15,3,2,'#7d7b76');rect(c,x+38,y-15,19,22,'#e8d8b6');rect(c,x+41,y-10,13,3,'#a2b2ad');rect(c,x+41,y-4,10,2,'#a2b2ad');rect(c,x-51,y-13,13,19,'#6d9a8d');rect(c,x-48,y-18,8,7,'#bfe3b2'); // postcard & mug
  // Cada estação tem uma pequena ferramenta visível de seu ofício.
  if(i===1){rect(c,x+44,y+3,17,9,'#dfc18b');rect(c,x+44,y+1,14,2,'#7a5553');}
  if(i===2){for(let k=0;k<4;k++)rect(c,x+40+k*5,y+4,4,5,['#e79c8c','#9dcfbd','#9bb9d6','#f7cb88'][k]);}
  if(i===3){rect(c,x+35,y+2,21,11,'#436384');rect(c,x+42,y+5,7,5,'#9cd5c0');}
  if(i===4){rect(c,x+44,y-10,6,18,'#263e4c');ellipse(c,x+47,y-14,5,6,'#7ba5aa');}
  if(i===5){rect(c,x+40,y+0,19,12,'#344658');rect(c,x+42,y+2,15,8,'#9acabd');}
  if(i===6){rect(c,x+43,y-9,8,21,'#ded8ad');rect(c,x+40,y-11,14,5,'#7e8a82');}
  if(i===7){rect(c,x+42,y+2,16,10,'#e1c29d');text(c,'↑',x+47,y+11,'#528878',12);}
}
function chair(c,x,y){ellipse(c,x,y+45,32,12,'#504744');rect(c,x-30,y+31,60,14,'#354554');rect(c,x-26,y+32,52,10,'#687f8e');rect(c,x-30,y+38,8,25,'#3d5367');rect(c,x+22,y+38,8,25,'#3d5367');rect(c,x-19,y+56,12,7,'#344557');rect(c,x+9,y+56,12,7,'#344557');}
function lamps(c){for(const x of [160,375,585,778,1038]){rect(c,x,151,3,17,'#394752');ellipse(c,x,175,25,8,'#e7ba83');rect(c,x-20,167,40,8,'#344657');rect(c,x-7,168,14,5,'#ffe6ad');}}
function officeBase(c){rect(c,0,0,SW,SH,'#101b2a');for(let x=0;x<SW;x+=25)rect(c,x,0,1,SH,'#182636');wall(c);floor(c);for(let y=191;y<739;y+=280){carpet(c,86,y,679,233);}divider(c);meeting(c);studio(c);lamps(c);for(let i=0;i<8;i++){const [x,y]=stations[i];desk(c,x,y,i);chair(c,x,y+60);} // plants, artboards, pathways
  plant(c,78,672,.7);plant(c,790,706,.8);plant(c,783,186,.65);rect(c,72,171,50,37,'#253b48');line(c,72,171,50,37,'#7c969b',3);text(c,'01',97,195,'#d8edb8',17,'center');rect(c,752,171,48,37,'#243c4b');text(c,'02',775,195,'#bed9cc',16,'center');for(let x=90;x<754;x+=18)if(noise(x,455)%6===0)rect(c,x,452,6,3,'#d2ad83');}
function avatar(c,x,y,i,selected=false,doing=false){const skin=['#e5ae87','#c88767','#edc6a0','#ae7961','#cfa081','#eab98e','#bc8968','#d9a678'][i];const hair=['#2b293d','#56382e','#6e443c','#342e3b','#403e48','#aa6645','#cfb18a','#292e43'][i];const top=['#9c99e4','#f1bc76','#78c5a7','#de9cba','#86b9dc','#e69b73','#b5cc86','#75c9be'][i];const float=doing?Math.floor(Date.now()/350)%2:0;const sx=Math.round(x),sy=Math.round(y-float);ellipse(c,sx,sy+24,21,7,'#4e5555');rect(c,sx-17,sy-1,36,24,top);rect(c,sx-22,sy+3,8,17,skin);rect(c,sx+17,sy+3,8,17,skin);rect(c,sx-14,sy+21,12,13,'#4d596f');rect(c,sx+7,sy+21,12,13,'#4d596f');rect(c,sx-15,sy+33,13,5,'#343843');rect(c,sx+7,sy+33,13,5,'#343843');rect(c,sx-12,sy-27,29,29,skin);rect(c,sx-15,sy-31,34,10,hair);rect(c,sx-16,sy-22,7,15,hair);rect(c,sx+16,sy-23,6,8,hair);rect(c,sx-5,sy-11,3,3,'#2e313b');rect(c,sx+9,sy-11,3,3,'#2e313b');rect(c,sx+1,sy-4,7,2,'#a26b5e');if(i===0){rect(c,sx-4,sy+2,6,16,'#f2d195');rect(c,sx-8,sy-13,14,6,'#62758e');}if(i===1){rect(c,sx-19,sy-31,31,6,'#5b402c');rect(c,sx+19,sy+5,4,18,'#e9c48f');}if(i===2){rect(c,sx-19,sy-31,39,5,'#8acfb6');rect(c,sx+3,sy+2,9,4,'#40876f');}if(i===3){rect(c,sx-17,sy-17,5,20,'#4e586c');rect(c,sx+17,sy-17,5,20,'#4e586c');}if(i===4){rect(c,sx+2,sy+7,6,5,'#e3e5d9');}if(i===5){rect(c,sx+6,sy+3,8,11,'#f2ddb9');}if(i===6){rect(c,sx-8,sy-13,12,7,'#6a5954');rect(c,sx+7,sy-13,12,7,'#6a5954');rect(c,sx+4,sy-11,4,2,'#6a5954');}if(i===7){rect(c,sx+7,sy+7,8,8,'#d5f5cf');}if(selected){line(c,sx-31,sy-40,63,82,'#ffe19d',3);star(c,sx,sy-48,'#f9dd8c');}}
function statusBar(c,x,y,i,label,status,selected){const active=['trabalhando','revisao'].includes(status);rect(c,x-66,y-12,133,29,'#1a2c3a');line(c,x-66,y-12,133,29,selected?'#f3ce89':active?'#78dbaa':'#75969b',2);text(c,label,x,y+1,'#f4e8d5',13,'center');const msg=active?'● em atividade':status==='aguardando'?'● aguardando':status==='concluido'?'● concluído':status==='erro'?'● erro':'● não conectado';text(c,msg,x,y+13,active?'#91efb6':'#aabdc3',9,'center');}
function drawScene(c,agents=[],selected=null){officeBase(c);agents.forEach((a,i)=>{if(!stations[i])return;const [x,y]=stations[i];const active=['trabalhando','revisao'].includes(a.status);avatar(c,x,y+111,i,a.id===selected,active);statusBar(c,x,y+173,i,a.nome,a.status,a.id===selected);});}

function motionForAgent(agent){
  if(agent.status==='concluido')return 'wave';
  if(agent.status==='revisao')return 'talk';
  if(agent.status!=='trabalhando')return 'idle';
  const profession={
    diretor:'talk',roteirista:'type',artista:'type',animador:'type',
    narrador:'talk',editor:'type',revisor:'talk',publicador:'wave'
  };
  return profession[agent.id]||'idle';
}
function paintPixelAgent(c,agent,i,x,y,selected,t,previewMotion,reduceMotion){
  const animator=window.VideoForgeAnimator;
  if(artMode!=='pixellab'||!spritesReady||!animator?.ready())return false;
  const motion=selected&&previewMotion?previewMotion:motionForAgent(agent);
  const direction=i<4?'south':'north';
  const frame=reduceMotion?0:Math.floor((t||0)/180)%4;
  if(!animator.draw(c,motion,direction,frame,x,y+111,88))return false;
  if(selected){line(c,x-38,y+67,76,90,'#ffe19d',2);star(c,x,y+61,'#f9dd8c');}
  return true;
}
window.VideoForgeArt={W:SW,H:SH,slots:stations,loadSprites,setArtMode,getArtMode:()=>artMode,
  spritesAvailable:()=>spritesReady,
  paintBackground:c=>(artMode==='pixellab'&&spritesReady?pixelBase(c):officeBase(c)),
  paintAgents:function(c,agents,selected,t,previewMotion=null,reduceMotion=false){
    agents.forEach((a,i)=>{
      if(!stations[i])return;
      const [x,y]=stations[i],isSelected=a.id===selected;
      const active=['trabalhando','revisao'].includes(a.status);
      if(!paintPixelAgent(c,a,i,x,y,isSelected,t,previewMotion,reduceMotion)){
        avatar(c,x,y+111,i,isSelected,active);
      }
      statusBar(c,x,y+173,i,a.nome||a.id,a.status,isSelected);
    });
  }};
