# Regra 2: camadas derivadas da imagem-mãe

Somente os agentes do **VideoForge** produzem imagens. A primeira cena
usa referência aprovada, quando houver, ou o próprio VideoForge cria uma
âncora visual. As cenas seguintes continuam usando essa âncora global
para manter identidade e técnica artística.

## Fluxo obrigatório de cada cena

1. Storyboard identifica explicitamente personagens e objetos móveis.
2. Artista visual gera a cena completa scene-N.png pelo Codex Proxy.
3. **Usando scene-N.png como imagem de entrada** na API de edição, o
   próprio Artista cria:
   - scene-N/background.png: fundo reconstruído, sem personagens ou props
     móveis, opaco e sem fantasmas.
   - scene-N/characters/<id>.png: personagem com fundo RGBA transparente
     real, escala, pose e coordenadas da cena original.
   - scene-N/movable_props/<id>.png: apenas o objeto móvel, PNG RGBA,
     sem braços/mãos; mesma orientação e lugar da cena original.
4. Revisor visual valida hashes, formatos, dimensões e presença de alfa
   real. Inspeção semântica, alinhamento de pixels, ausência de fantasmas
   e fidelidade ainda exigem aprovação visual independente.
5. Animador envia camadas ao Remotion MasterShort com renderMode
   multilayer, background e layers para personagens e props.
6. Editor monta MP4; Revisor confere MP4. Publicador não é acionado.

Objetos fixos ficam no fundo. Quando não há personagens ou props
independentes, a cena-mãe é o próprio background, sem chamada adicional.

## Manifesto e custo

A raiz do manifesto precisa conter:

    "scene_decomposition": {
      "schema": "videoforge/scene-decomposition/v1",
      "mode": "layered_from_master_scene",
      "require_transparent_rgba": true,
      "require_independent_visual_review": true
    }

Cada cena inclui um layer_plan:

    "layer_plan": {
      "characters": [
        {"id":"pesquisadora","description":"Personagem em casaco azul na mesma pose"}
      ],
      "movable_props": [
        {"id":"caderno","description":"Caderno antigo que a protagonista segura"}
      ]
    }

Lista vazia é permitida. Máximo: três personagens e três props por cena.
O storyboard não inventa objetos durante a geração de imagens.

Orçamento = imagens-mãe + fundos a limpar + personagens separados +
objetos separados. O exemplo contém 8 imagens-mãe + 8 fundos + 8
personagens + 2 props = 26 requisições. Limite global 48. O workflow
manual exige aprovação explícita de custo para TODAS as chamadas;
uma execução antiga de 8 chamadas não ganha orçamento maior sozinha.

## Artefatos e QA

- imagens.json: hashes das cenas-mãe e continuidade global.
- scene-layers.json: caminhos, SHA-256 das camadas e hash da cena-mãe.
- qa-camadas.json: verificação técnica do alfa, dimensão e proveniência;
  o campo approved_for_youtube permanece false.
- qa-imagens.json, qa-editorial.json: revisão visual independente pendente.
- remotion-props.json: composição real de camadas.
- video.mp4: somente prévia privada.

O Remotion fixado no AutoEditorVideo suporta imagens com canal alfa
em camadas front_character e hero_prop. Permite movimentos discretos
de personagem sem deformação. Os props estão separados para animação,
mas hero_prop permanece estático no renderizador atual: **não inventar
movimento articulado ou dizer que rigging já existe**.

## Responsabilidades e testes

- Ilustrador/Artista: desenha e deriva PNGs usando o Codex Proxy.
- Revisor visual: testa arquivos, alfas, referências e registra bloqueios.
- Animador: organiza imagens RGBA e gera propriedades multilayer.
- Editor: executa render Remotion e valida entrega de MP4.
- Revisor técnico: confere MP4 final e mantém QA editorial pendente.
- Publicador: não trabalha; upload desativado.

O DAG em geradores/autoeditor/gerador.json descreve as dependências.
Os testes offline tests/test_scene_layers.py usam um Proxy simulado.

Em falha, não usar substitutos locais gerados por Pillow, não gerar
imagens pelo chat, não fazer retry automático nem publicar. Um PNG
com bytes corretos não basta para provar encaixe real ou identidade:
a revisão humana continua obrigatória.
