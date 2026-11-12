# Motor de animação Remotion — referência Fofinho EP01 Parte 3

## Origem técnica usada

- `HelioConde/AutoEditorVideo/motion-remotion/src/emanuelly-layer-stage.tsx`: movimento independente de personagens, ovo, gotinhas e gatinho por quadro.
- `HelioConde/AutoEditorVideo/motion-remotion/src/fofinhos-ambient-effects.tsx`: borboletas, nuvens, pétalas e pontos de luz deterministas.
- `HelioConde/AutoEditorVideo/conteudos/fofinhos-ep01-parte03-roteiro-longo-v1.json`: 18 trechos narrativos (mover patinha, gotas, jardim, carinho).
- `HelioConde/AutoEditorVideo/scripts/kids_fofinho_storyboards_v2.py`: poses oficiais do Fofinho e roteiro resumido por cenas.
- Motor Remotion fixado no commit `ec85db5bc74455122e4501aba05bd2dd3fd0df2c`.

**Importante**: 2D sprite motion não é rigging de ossos. O motor não modifica a pele nem articula uma patinha desenhada dentro de um personagem opaco. Para animar a patinha, ela deve ser PNG RGBA independente e o corpo-base deve ter a patinha removida sem fantasmas. A análise de encaixe final depende de revisão humana.

## Aplicação no VideoForge

O VideoForge continua proprietário de toda a mídia. O chat não cria desenhos.
A primeira imagem do vídeo fixa a identidade. Cada cena-mãe gera seu fundo
limpo e camadas RGBA; agora o Artista pode gerar também
`character_parts` (mão, patinha, braço, cabeça etc. somente se o
Storyboard as solicitou). Cada parte adicional custa **uma** edição
de imagem pelo mesmo Codex Proxy, contabilizada antes do gasto.

O Storyboard escreve uma lista de `motion_plan.cues` para cada cena, com:
- `id`: ID idêntico ao PNG RGBA extraído da cena;
- `motion`: movimento permitido conforme o tipo da camada;
- `start` e `end`: fração de 0 a 1 da duração da própria cena;
- `distance`: amplitude de 0 a 46 px.

Funções permitidas:
- Personagem inteiro: `idle`, `walk`, `approach`, `hop`, `snuggle`, `still`.
- Parte isolada: `paw-lift`, `paw-wave`, `pat`, `sway`, `still`.
- Objeto/magia: `float`, `rise`, `fall`, `orbit`, `bounce`, `sway`, `pulse`, `pop`, `settle`, `still`.

O animador recusa agentes inexistentes, ordem/intervalos inválidos,
objetos sem PNG separado e tentativas de levantar patinha por
transformação do corpo inteiro. O componente
`videoforge/motion/videoforge-motion.ts` aplica movimento determinista
por frame, sem `Math.random`, chamadas de IA, stretching não uniforme
ou geração adicional de imagens. Para evitar alterações não rastreáveis
do AutoEditorVideo, `videoforge/motion/remotion_overlay.py` verifica
a versão pinada, copia somente este módulo e aplica substituições
pontuais em `master-short.tsx` no **checkout temporário de render**.

O atual `MasterShort` aceita `Scene.layers` e agora usa
`layer.motion` quando ele existe. Sem `motion`, mantém o
comportamento estático/idle anterior. O Animador valida
`remotion-props.json` e grava `qa-motion.json`; o Editor renderiza
somente na etapa posterior. O Revisor técnico examina o MP4; o
revisor humano ainda precisa validar contatos, limpezas, camadas e
movimentos.

## Parte 3 como guia fiel, não vídeo pronto

`canal/manu-kids/fofinho-parte03-motion-blueprint.json` contém os
**18 trechos da história longa** da Parte 3, em modo `plan_only`.
O plano preserva o **mesmo Fofinho azul e a mesma Emanuelly** e
refere-se a: gotinha subindo/descendo, patinha separada, dança de 3
gotas, pulos, bolha, chuva leve, jardim, borboletas, flor regada e
carinho. Nenhum ovo reaparece após o nascimento, e não há antecipação
do abraço mágico da Parte 4.

Esse plano **não** garante que as artes/poses particulares tenham sido
extraídas ou que um vídeo de 18 trechos possa ser renderizado sem
planejamento de cenas, narração e orçamento. É uma especificação
editorial a ser ligada aos recursos oficiais quando os agentes
produzirem esse capítulo.

## Verificação obrigatória dos funcionários

- **Roteirista/Storyboard:** descreve o movimento e identifica os PNGs
  necessários.
- **Artista:** produz exclusivamente as imagens-mãe, backgrounds,
  personagens e partes isoladas pelo Codex Proxy.
- **Revisor visual:** valida alfa, origem e dimensões; visualmente
  ainda é necessário aprovar ausência de fantasmas.
- **Animador:** valida `motion_plan` e gera plano Remotion auditado;
  movimentos por camada, não por zoom da cena inteira.
- **Editor:** renderiza MP4, sem decidir desenho ou alterações de roteiro.
- **Revisor:** QA do MP4 e compatibilidade dos movimentos com a cena.
- **Publicador:** desativado em todas as prévias.

**Testes automáticos em toda mudança:** `tests/test_fofinho_motion.py`
verifica regras e funções; o GitHub Actions faz `npm ci`, executa
`apply_motion_overlay` no Remotion pinado, `npm run typecheck` e
`tests/test_fofinho_motion.cjs` nos frames reais em TypeScript,
sem imagem/voz paga ou upload.

Nenhum resultado de teste é aprovação artística do novo MP4: verificação
humana de contato, continuidade, poses e perspectiva permanece pendente.
