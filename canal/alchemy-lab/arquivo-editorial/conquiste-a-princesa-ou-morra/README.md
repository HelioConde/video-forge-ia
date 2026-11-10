# Conquiste a Princesa ou Morra! — Bíblia narrativa e visual (v1)

> **Série original em estilo anime/dorama de fantasia, romance, suspense e sistema de missões.**
> **Canal piloto:** Alchemy Lab (chave `alchemy`; YouTube Channel ID `UCCTYFE5Cmz2aYZ37cJQ-wcg`).
> **Data da decisão:** 10/11/2026. **Estado:** bíblia e roteiro editorial; **não** representa imagens, MP4 ou upload gerados.
> **Classificação editorial:** ficção para público geral, não voltada especificamente a crianças.

## Premissa imutável

Ren é um jovem plebeu de 21 anos ridicularizado por fracassar sete vezes no exame dos cavaleiros. Depois de virar ajudante do arquivo real, é falsamente acusado de roubar o selo do rei e levado ao julgamento. De joelhos diante do trono, enquanto a execução é anunciada, um menu azul que **somente ele consegue ver** aparece:

- **MISSÃO PRINCIPAL:** conquistar o coração da princesa Elara, sem manipular seus sentimentos.
- **PRAZO:** 30 dias.
- **FALHA:** morte definitiva.
- **MISSÃO DE EMERGÊNCIA (EP01):** fazer a princesa suspender a execução em 90 segundos.

O sistema concede tarefas e informações limitadas, **não** controla as emoções de Elara. Nenhum nível, recompensa ou afinidade substitui a escolha da princesa. Ren precisa sobreviver, reconstruir sua reputação e descobrir por que foi incriminado. O romance é construído por decisões e confiança, não por um truque de pontuação.

## Elenco canônico — identidade travada

- **REN (ID: REN-01, 21 anos):** jovem adulto, cabelo preto curto e levemente desalinhado, olhos castanho-âmbar, sobrancelha esquerda com pequena cicatriz vertical, pele morena clara, porte magro; túnica azul-escura surrada, camisa bege, cinto marrom com fivela de ferro simples, calças grafite e botas marrons. **Exatamente a mesma roupa e cicatriz** no julgamento, na academia e no arquivo (no passado a roupa pode estar limpa; sujeira de cena é uma camada separada). Expressões variam; rosto e proporções não.
- **ELARA (ID: ELARA-01, 22 anos):** jovem adulta, cabelo prateado longo com trança fina à direita, olhos violeta-acinzentados, pequena pinta sob o olho esquerdo, tiara prateada com gema azul, vestido azul-noite com bordado prateado e mangas longas. Inteligente, corajosa e cautelosa; não é um objeto ou recompensa e não se apaixona imediatamente.
- **REI VALDREN (ID: VALDREN-01, 52 anos):** cabelo grisalho penteado para trás, barba curta quadrada, olhos verdes, coroa de ouro com rubi central, manto bordô e armadura preta com detalhes dourados. Rosto, coroa e insígnias fixos.
- **CAPITÃO OREN (ID: OREN-01, 39 anos):** cabelo castanho muito curto, cicatriz no maxilar direito, armadura cinza escura com escudo branco no peito; comanda os guardas. Não é automaticamente o traidor.
- **INTRUSO (ID: LUVA-01):** rosto **não revelado** no EP01; somente mão esquerda com luva preta e anel de prata em forma de serpente, com olho de pedra vermelha. Não mostrar rosto/silhueta identificável prematuramente.

## Cenários oficiais — sem regeneração independente

1. **TRONO-01:** salão simétrico de pedra cinza, piso de mármore com círculo solar, dois vitrais altos azuis, colunas com fitas bordô, trono de ouro envelhecido sobre três degraus; no julgamento, princesa fica à direita do trono e Ren ajoelhado no círculo solar. Manter geometria, direção da luz, posição do trono, altura dos degraus e portas.
2. **ACADEMIA-01:** pátio retangular de treinamento com 3 arcos de pedra, estandarte azul com leão branco, piso de terra, torre ao fundo; flashback preserva o layout.
3. **ARQUIVO-01:** arquivo real com duas estantes de carvalho, mesa à esquerda, vitral circular ao fundo e pedestal de vidro do selo à direita. O selo verdadeiro e o falso têm design individual fixado; usar os mesmos modelos, nunca trocar detalhes.
4. **CORREDOR-01:** passagem do castelo com tochas, arcos baixos e uma janela estreita à esquerda. Só entra quando a cena exige.

## Objetos que jamais podem variar

- **SELO-REAL-VERDADEIRO (PROP-01):** disco de ouro de oito centímetros, leão em relevo olhando **à esquerda** e microfissura diagonal na borda inferior direita.
- **SELO-FALSO (PROP-02):** disco dourado do mesmo tamanho, mas leão olhando **à direita**, sem microfissura; é este que aparece como prova no julgamento. Não mostrar os dois com mesmo relevo.
- **ESPADA-CARRASCO (PROP-03):** espada longa de aço escurecido, guarda reta e cabo preto com três faixas de couro; modelo único.
- **MENU-DESTINO (UI-01):** painel 2D de vidro escuro translúcido, borda ciano, texto branco, cabeçalho fixo `SISTEMA DO DESTINO`, marca de caveira vermelha somente nas consequências fatais, mesma tipografia/layout/ícones/resolução em todos os episódios. O conteúdo e contagem podem atualizar, **o desenho nunca muda**.
- **AVISO-ANOMALIA (UI-02):** mesmo painel UI-01 com tarja vermelha inferior; não é outra interface visual.

## Regras rigorosas de continuidade — padrão Fofinhos

1. **Gerar e aprovar uma única folha de referências por personagem, cenário, objeto e UI antes das cenas.** Identificar cada `anchor_id`, caminho do arquivo e SHA-256 reais, sem inventá-los. Enquanto não houver referência, marcar `pending`.
2. Todas as poses/cenas são **edições derivadas das âncoras reais**, não recriações a partir do nome ou do prompt isolado. Preservar cabelo, roupas, olhos, cicatrizes, acessórios, estruturas, objetos e paleta.
3. Reutilizar o **mesmo fundo aprovado** por cenário; câmera pode reenquadrar. Flashback usa o mesmo cânone com tratamento de luz/cor (âmbar e vinheta suave) e título discreto `7 DIAS ANTES`, sem trocar figurino, arquitetura ou características.
4. Personagens, elementos interativos, espada, selo, fundo, sombra, legenda e menu devem ser **camadas independentes**, com ordem Z e oclusão checadas. A UI é composta no Remotion/pós-produção em vez de ser redesenhada por prompt de imagem.
5. Proibir mãos extras, faces alteradas, anatomia impossível, cicatriz desaparecida, personagem fora de escala, luz incoerente, selo invertido por espelhamento da imagem, vitral/portas mudando de lado e texto do menu ilegível.
6. Não usar zoom/pan como substituto de animação: movimentos expressivos de olhos/cabeça/braços com poses fiéis ou rigging suave, sem tremor ou deformação; QA visual em vídeo real.
7. Não antecipar spoilers: rosto do intruso fica oculto; Elara **não vê o painel de Ren**, embora conheça o conceito de missões. Isso é mistério do mundo a resolver depois.
8. Legenda PT-BR precisa, voz natural e diferenciada por personagem; trilha com licença checada, voz inteligível, sem copiar cenas, músicas ou personagens de animes existentes.
9. Quando trocar de flashback para julgamento, restaurar exatamente o arranjo do presente; marcar o tempo em storyboard e transições de áudio.
10. **Bloquear render/publicação se faltarem âncoras, não houver QA visual, o vídeo estiver fora de 150–180 segundos ou o Channel ID/OAuth não corresponder a Alchemy.** Registrar evidência e recibo, não confiar somente em `Actions success`.

## Arco da temporada 1 — seis episódios (planos; somente EP01 reservado)

| Ep. | Título provisório | Gancho e avanço |
|---|---|---|
| 01 | O Fracassado Condenado | Julgamento → flashbacks do fracasso e armadilha → missão mortal → Elara suspende a execução → ela conhece o sistema |
| 02 | A Princesa de Gelo | Ren vira assistente vigiado; missão proteger alguém que Elara desconfia; primeira cooperação real |
| 03 | O Anel de Serpente | Um novo flashback e uma pista ligam o intruso ao roubo; suspeitas falsas e custos de uma missão |
| 04 | O Baile das Máscaras | Ren recebe missão social aparentemente romântica; Elara revela seu próprio objetivo político |
| 05 | Quem Controla o Destino? | Uma ação correta diminui a afinidade; Ren questiona o sistema e arrisca a própria vida |
| 06 | O Preço de uma Escolha | O mistério do selo se conecta à origem das missões; Elara decide se confia em Ren |

**Não transformar os episódios planejados em roteiros prontos nem reservá-los sem curadoria/checagem.** Uma única temporada não deve exigir que Elara se apaixone por ordem de um algoritmo.

## Produção / análise do experimento

- **Arquivo de roteiro/storyboard EP01:** [episodio-01.json](episodio-01.json), com texto por cena, falas e horários.
- **Reserva antes de produzir:** `conteudos/otaku-production-reservations.json`, canal `alchemy`, ID `alchemy-114-conquiste-princesa-ep01`, owner `alchemy_dorama_original_20261110`.
- **Duração exata alvo:** 175 s, mínimo 150, máximo 180; confirmar áudio TTS antes de render. Vertical **1080×1920, 9:16**.
- **Estado editorial:** roteiro, bíblia, compositor Remotion e pré-validador de referências criados. `reference_images_generated=false`, `voice_generated=false`, `rendered=false`, `uploaded=false`. Não houve geração de MP4.
- **Sem disparar workflows, gastar chamadas de imagem ou alterar fila, nicho, nome, autenticação ou vídeos existentes.** Testar em separado porque o tema de fantasia/anime difere do nicho atual do Alchemy.
- Quando houver vídeo aprovado e publicação autorizada, comparar desempenho nas mesmas janelas de 24h/48h/7 dias, retenção nos primeiros 30s, média assistida, engajamento e inscritos por mil views. Não tratar visualizações iniciais como veredito.
\n\n## Motor de animação — mesma tecnologia do Fofinho EP1 Parte 3\n\nDecisão do criador em **10/11/2026**: reutilizar no Alchemy a estratégia técnica exata de **camadas PNG independentes + Remotion + movimentos de sprites + poses ancoradas**, usada no Fofinho EP1 Parte 3. **Não** reutilizar o elenco/assets/músicas ou executável infantil diretamente: o motor Kids possui limite específico de 60 segundos e `madeForKids=true`. Este projeto usa adaptação isolada, sem mudar nenhum script Kids.\n\n**Referência canônica do Fofinho:** `scripts/kids_emanuelly_todos_videos_v2.py` (planejamento, hashes, sincronismo, MP4 e QA) e `motion-remotion/src/emanuelly-layer-stage.tsx` (palco 2D de camadas).\n\n**Implementação isolada Alchemy:** `scripts/alchemy_dorama_original.py` (pré-validador, cópia de PNGs aprovados, props por cena, render local), `motion-remotion/src/alchemy-dorama-short.tsx` (animação de personagens e objetos individualmente, cenário reutilizado, flashbacks e menu vetorial) e composição `AlchemyDoramaOriginal` em `motion-remotion/src/root.tsx`. **Não é rigging completo nem IA de vídeo**; poses de braços, passos e expressões precisam de recursos aprovados e revisão humana.\n\n**Bíblia de recursos:** [referencias-v1.json](referencias-v1.json) contém IDs, caminho local esperado, `sha256` e `approved`. Todos começam **pendentes**; nenhum PNG foi gerado ou aprovado nesta etapa. Imagens de personagens/objetos devem ter transparência RGBA verdadeira. O menu de missões é um componente vetorial 2D fixo, sem pedir que IA redesenhe letras/telas.\n\n### Comando único (sem upload)\n\nA partir da raiz do projeto no Windows, após atualizar sua cópia e instalar as dependências do Remotion:\n\n```powershell\n.\\autoeditor.ps1 -Canal alchemy -Acao dorama-planejar -Id alchemy-114-conquiste-princesa-ep01\n```\n\nDepois de criar e aprovar **todas** as referências reais no diretório `assets/gerados/alchemy-dorama-original/referencias/`, preencher os hashes reais e marcar aprovação visual da UI em `referencias-v1.json`. Além disso, adicionar narração verdadeira `assets/gerados/alchemy-dorama-original/ep01/narracao.mp3` e `legendas.json` com timestamps em frames vindos da fala. Só então estão disponíveis:\n\n```powershell\n.\\autoeditor.ps1 -Canal alchemy -Acao dorama-preparar -Id alchemy-114-conquiste-princesa-ep01\n.\\autoeditor.ps1 -Canal alchemy -Acao dorama-renderizar -Id alchemy-114-conquiste-princesa-ep01\n```\n\n**Atenção:** esses dois comandos serão **bloqueados** enquanto houver imagens, aprovação, timestamps, áudio ou ferramentas ausentes. O render é só para revisão local; produz `assets/gerados/alchemy-dorama-original/ep01/final-camadas.mp4`, não faz upload e nunca modifica o Fofinho ou a programação diária. Não haverá remendo de rosto, troca de figurino ou cópia de música Kids.\n\n**QA offline:** `tests/test_alchemy_dorama_original.py` e `.github/workflows/alchemy-dorama-offline.yml`; aprovação audiovisual real depende de assistir ao vídeo completo, não só de CI verde.\n

## Nova regra aprovada — quadro-mestre e camadas transparentes (teste de 10 segundos)

Decisão do criador em 10/11/2026: **não** gerar fundo/personagens independentes de prompts de texto. Em vez disso:
1. Gerar **UMA imagem-mestra completa**, anime cinematográfico, trono com rei, Ren ajoelhado, Elara, espada, tudo na mesma composição.
2. Salvar SHA-256 do PNG mestre. Em TODAS as cinco edições seguintes chamar images/edits, fornecendo os bytes reais **daquela mesma imagem-mestra** como referência — nunca uma pose ou imagem de outro projeto.
3. Extrair no mesmo canvas de 1024×1536 (sem recentralizar): fundo vazio inpaint, Ren transparente, rei transparente sem trono, Elara transparente, espada+mão transparentes; guardar SHA-256 do mestre em cada derivado.
4. Renderizar as camadas de personagens e espada individualmente, na mesma perspectiva e localização do mestre. Painel de missões vetorial separado.
5. Teste restrito a **10 segundos / 300 frames / 30 fps / 1080×1920**. Som ambiente original gerado localmente, sem narração robótica neste teste exclusivamente visual. Não altera ou publica o episódio de 175s.
6. Inspecionar **mestre x quadro composto** antes de aprovar; bloquear publicação até confirmar recortes, proporção, continuidade, oclusão e movimento. Separar sprites não significa rigging articulado.

Implementação:
- scripts/alchemy_dorama_master_10s.py: máximo 6 chamadas (mestre + 5 edições do mesmo mestre), RGBA, manifesto de SHA-256, revisão pendente, modo de reúso ALCH10_REUSE_ONLY=1 MAX_IMAGE_CALLS=0.
- motion-remotion/src/alchemy-dorama-master-10s.tsx: composição AlchemyDoramaMaster10s, animação isolada de Ren, rei, Elara, espada e UI; 300 quadros.
- tests/test_alchemy_dorama_master_10s.py: testes de integridade, proveniência e rejeição de imagem sem alpha.
- .github/workflows/alchemy-dorama-master-10s-test.yml: executa uma vez no CI, salva MP4, imagem-mestra, PNGs, comparação e QA no artifact alchemy-dorama-10s-imagem-mestra-camadas; sem YouTube.

Comando na raiz do projeto Windows para planejar, sem consumir imagens:
    .\autoeditor.ps1 -Canal alchemy -Acao dorama-teste10-planejar -Id alchemy-114-conquiste-princesa-ep01

Para gerar localmente com proxy de imagem devidamente configurado:
    .\autoeditor.ps1 -Canal alchemy -Acao dorama-teste10-gerar -Id alchemy-114-conquiste-princesa-ep01

IMPORTANTE: gerar personagem isolado não proporciona por si só animação real de mãos/cabeça/boca. Se este teste de 10s não parecer convincente, criar partes/poses derivadas da imagem-mestra, validar a identidade e aplicar rigging individual ANTES de produzir novo episódio longo.


## Referência canônica do criador — substituição da arte-mestra (10/11/2026)

**Criador rejeitou o teste anterior de 10 segundos**, porque o motor gerou um quadro-mestre novo por prompt sem utilizar literalmente a imagem aprovada. A referência válida passa a ser EXATAMENTE o PNG de 941×1672 exibido no chat com Ren ajoelhado à esquerda, Valdren no trono, Elara à direita, o menu de missões, a espada em primeiro plano e pequeno flashback no alto. Para a cena reconstruída, remover as sobreposições/flashback pela edição do fundo, manter os personagens e compor a UI separadamente; nunca gerar outro quadro-mestre.

**Caminho obrigatório de origem no repositório:** `canais/alchemy-lab/conteudos/conquiste-a-princesa-ou-morra/referencia-aprovada-20261110.png`.

**SHA-256 exato do PNG enviado pelo criador:** `4b3f9ebf534537b1fb862d8df0167ca5730007b485ae04d40e3ce055a518c0b2`.

O arquivo binário original **precisa ser colocado neste caminho**, pois não deve ser reconstruído, recomprimido, renomeado erroneamente nem substituído por imagem semelhante. O script `scripts/alchemy_dorama_master_10s.py` verifica este SHA antes de usar qualquer chamada ao proxy, converte o mesmo PNG em canvas 1024×1536 por padding lateral para preservar a composição e somente então extrai `background`, `ren`, `king`, `elara` e `sword` por cinco edições reais da MESMA referência. Se faltar o original, a execução BLOQUEIA sem consumir imagens. **Não mais chamar `/v1/images/generations` para criar a arte-mestra.** Limite da retomada: 5 edições; não 6.

**Status da referência:** aprovação editorial da aparência feita pelo criador; a inclusão dos bytes originais no GitHub deve ser verificada antes de rodar o workflow. A arte antiga do run 42781369081 fica como arquivo histórico rejeitado e NÃO substitui este PNG. O MP4 antigo não é reutilizado.

**Comando após incluir o arquivo na pasta:** `python scripts/alchemy_dorama_master_10s.py --acao gerar` (com proxy de imagens ativo e `MAX_IMAGE_CALLS=5`, `IMAGE_MODEL=gpt-image-2`). O workflow `alchemy-dorama-master-10s-test.yml` só produz a nova prévia na main sob o commit `run(alchemy): 10s creator-approved pinned reference only`; não publica vídeos no YouTube.
