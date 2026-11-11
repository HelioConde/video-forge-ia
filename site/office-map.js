/* Posições calibradas para a sede única gerada no PixelLab (688x384).
   Sprite final: site/assets/pixellab/scenes/agencia-unificada.png.
   O Canvas mantém o mundo 1280x820; y+111 é o centro do avatar.
   As salas são ZONAS do mesmo edifício, não edifícios independentes.
   'preview' significa somente ambiente ilustrativo, sem IA executora. */
(() => {
  "use strict";
  const scene=Object.freeze({
    source:Object.freeze({x:96,y:54,w:492,h:285}),
    target:Object.freeze({x:46,y:110,w:1188,h:660}),
    size:Object.freeze({width:688,height:384}),
    provenance:"PixelLab v2 / GitHub Actions 43039103117",
  });
  const rooms=Object.freeze({
    production:{x:170,y:220,w:295,h:480,label:"PRODUÇÃO",status:"approved"},
    creative:{x:525,y:222,w:288,h:258,label:"SALA CRIATIVA",status:"approved"},
    media:{x:943,y:222,w:285,h:258,label:"ÁUDIO & EDIÇÃO",status:"approved"},
    breakroom:{x:803,y:484,w:170,h:208,label:"COPA & ÁGUA",status:"preview"},
    games:{x:974,y:484,w:145,h:208,label:"SALA DE JOGOS",status:"preview"},
    restroom:{x:1120,y:484,w:109,h:208,label:"WC",status:"preview"}
  });
  // A imagem contém os assentos: usar a mesma correção para os oito agentes.
  // O ajuste é aplicado apenas no desenho de 'sit', não às rotas de caminhada.
  const seat=Object.freeze({dx:0,dy:14,direction:"north"});
  // Escala única para a equipe; amplia o atlas sem redesenhar sprites PixelLab.
  const character=Object.freeze({seatedSize:88,standingSize:84,labelOffset:70});
  const stations=Object.freeze([
    {id:"diretor",x:255,y:254,room:"production"},
    {id:"roteirista",x:394,y:254,room:"production"},
    {id:"artista",x:592,y:254,room:"creative"},
    {id:"animador",x:739,y:254,room:"creative"},
    {id:"narrador",x:1007,y:254,room:"media"},
    {id:"editor",x:1124,y:254,room:"media"},
    {id:"revisor",x:255,y:449,room:"production"},
    {id:"publicador",x:384,y:449,room:"production"}
  ]);
  const destinations=Object.freeze({
    coffee:Object.freeze({x:857,y:572,label:"Máquina de café (prévia)",room:"breakroom"}),
    water:Object.freeze({x:916,y:572,label:"Bebedouro (prévia)",room:"breakroom"}),
    games:Object.freeze({x:1052,y:598,label:"Salão de jogos (prévia)",room:"games"}),
    restroom:Object.freeze({x:1167,y:579,label:"Entrada do WC (prévia)",room:"restroom"})
  });
  // Conversas no corredor, à frente da mesa colaborativa.
  const meetings=Object.freeze([{x:591,y:457},{x:710,y:457}]);
  const navigation=Object.freeze({hallY:454,westAisleX:446});
  window.VideoForgeOfficeMap=Object.freeze({scene,rooms,stations,seat,character,destinations,meetings,navigation});
})();
