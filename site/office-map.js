/* Fonte única de posições do escritório: cômodos, portas e alvos de rotas.
   'preview' indica cenários ilustrativos, não instalações físicas com IA. */
(() => {
  "use strict";
  const rooms=Object.freeze({
    production:{x:79,y:194,w:512,h:512,label:"PRODUÇÃO",status:"approved"},
    creative:{x:655,y:196,w:256,h:256,label:"SALA CRIATIVA",status:"approved"},
    media:{x:954,y:196,w:256,h:256,label:"LABORATÓRIO",status:"approved"},
    breakroom:{x:640,y:488,w:267,h:216,label:"COPA & ÁGUA",status:"preview"},
    games:{x:912,y:488,w:170,h:216,label:"SALA DE JOGOS",status:"preview"},
    restroom:{x:1088,y:488,w:127,h:216,label:"WC",status:"preview"}
  });
  const destinations=Object.freeze({
    coffee:Object.freeze({x:704,y:614,label:"Máquina de café (prévia)",room:"breakroom"}),
    water:Object.freeze({x:854,y:614,label:"Bebedouro (prévia)",room:"breakroom"}),
    games:Object.freeze({x:998,y:644,label:"Sala de jogos (prévia)",room:"games"}),
    restroom:Object.freeze({x:1152,y:630,label:"Entrada do banheiro (prévia)",room:"restroom"})
  });
  const meetings=Object.freeze([{x:729,y:369},{x:834,y:369}]);
  window.VideoForgeOfficeMap=Object.freeze({rooms,destinations,meetings});
})();