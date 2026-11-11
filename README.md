# VideoForge AI

**Gerador modular de vídeos com IA e publicação automatizada no YouTube.**

> **Estado atual: estrutura e testes (dry-run).** Ainda não gera MP4, não chama provedores de IA e não faz upload.

## Organização do projeto

Os cinco canais do AutoEditorVideo estão separados em pastas independentes. Cada canal possui suas próprias regras editoriais e um modelo padrão, que pode ser substituído individualmente em um vídeo.

```text
video-forte-ia/
├── canal/
│   ├── otaku-br/        # Otaku Multicena
│   ├── otaku-en/        # Otaku Reframe
│   ├── gamer/           # Conde Games (marca proposta)
│   ├── manu-kids/       # Emanuelly Kids / Manu Kids
│   └── alchemy-lab/     # Alchemy Lab
│       └── videos/teste-10s/
├── modelos/
│   ├── camadas-animadas/modelo.json
│   └── imagem-estatica/modelo.json
├── videoforge/
├── tests/
├── docs/
└── .github/workflows/
```

Cada canal contém `canal.json`, `conteudos/indice.json`, `README.md` e `videos/`. Referências históricas selecionadas ficam em `arquivo-editorial/` e **não** podem ser usadas como manifestos executáveis.

Confira o [catálogo dos canais](canal/README.md) e o [relatório de migração](docs/MIGRACAO_AUTOEDITORVIDEO.md).

### Como funciona a escolha do modelo

Cada canal tem seu próprio `modelo_padrao` no `canal.json`.
Um vídeo pode optar por `"modelo": "camadas-animadas"` no próprio `video.json`. Sem a propriedade, herda o padrão do canal; as escolhas iniciais são provisórias.

Cada modelo de produção também reserva configurações distintas de **provedor e modelo de IA por etapa** (roteiro, imagem, animação, voz), ainda pendentes de implementação.

Leia [canal/README.md](canal/README.md) e [modelos/README.md](modelos/README.md).

## Regra permanente de organização

**A organização do VideoForge AI é uma exigência contínua, em toda alteração — não apenas na criação do projeto.** Antes de adicionar, alterar, mover ou remover qualquer código, configuração, modelo, vídeo ou automação, é obrigatório preservar uma estrutura clara, consistente e fácil de manter.

- Manter cada canal em `canal/<id>/`, seus vídeos em `canal/<id>/videos/<id>/` e os modelos reutilizáveis em `modelos/<id>/`.
- Separar responsabilidades por módulos; evitar arquivos gigantes, código duplicado e funcionalidades sem relação misturadas no mesmo arquivo.
- Usar nomes descritivos e consistentes para arquivos, pastas, funções e configurações. Não criar scripts ou pastas temporárias sem necessidade.
- Reaproveitar componentes e modelos compartilhados sem comprometer o isolamento dos canais; permitir um modelo próprio por vídeo.
- Manter arquivos gerados, mídias, logs e credenciais fora do código versionado e nos lugares definidos pela arquitetura.
- Ao concluir qualquer alteração, revisar a estrutura, remover apenas artefatos realmente obsoletos com segurança, atualizar a documentação e executar os testes pertinentes.
- Se uma mudança exigir nova pasta ou módulo, justificar sua responsabilidade, respeitar os padrões existentes e atualizar este guia.
- Não reorganizar nem excluir conteúdo de outros canais sem necessidade e sem verificar referências e dependências.

As orientações operacionais para agentes de IA e colaboradores estão em [AGENTS.md](AGENTS.md).

## Escritório virtual de agentes (GitHub Pages)

O escritório **Pixel Studio v3** usa Canvas 2D em tela inteira, com pixel-art original, oito funcionários personalizados, sala criativa, estúdio audiovisual e cinco canais. Oferece zoom/arraste, seleção direta, minimapa recolhível no celular e painel flutuante. Os oito papéis e suas dependências ficam centralizados em [agentes/equipe.json](agentes/equipe.json). Os trabalhadores aparecem como **não conectados** até receberem eventos reais do backend. A publicação é **automática quando o painel, agentes, canais ou testes relacionados mudarem na branch `main`**; também aceita execução manual. O GitHub Pages precisa estar configurado com a opção GitHub Actions.

Veja [site/README.md](site/README.md) e [docs/ESCRITORIO_AGENTES.md](docs/ESCRITORIO_AGENTES.md). **Não confundir a página visual com agentes já executando tarefas.**

## Geração de personagens com PixelLab

O [workflow PixelLab](.github/workflows/pixellab-character.yml) permite planejar gratuitamente, criar um personagem em oito direções, animar movimentos, produzir estados/poses como sentado ou digitando e exportar spritesheets. Já existe o [perfil Alex](personagens/alex/profile.json). O programa pode reconhecer um personagem previamente criado em sua conta, quando não houver ambiguidade.

A API precisa de `PIXELLAB_API_TOKEN` cadastrado em GitHub Secrets. No repositório público, as chamadas pagas e a exportação de ZIPs requerem autorizações explícitas. **Nenhuma geração paga foi executada apenas com a instalação do código.**

[Instruções de configuração e execução](docs/PIXELLAB.md).

### Produção em lote pelo ChatGPT Work

O [workflow PixelLab para Work](.github/workflows/pixellab-work.yml) permite **planejar ou gerar automaticamente até 8 direções ausentes por execução**, sem recriar o personagem base. Ele consulta os grupos existentes, reutiliza `animation_group_id` e evita duplicatas; repetições devem ser sequenciais e verificadas entre rodadas.

É obrigatório selecionar o personagem correto no Secret `PIXELLAB_CHARACTER_ID`: foram encontradas **27 bases** na conta, portanto não é seguro escolher uma automaticamente. Por padrão o workflow é apenas leitura; solicita confirmação de custo e visibilidade de artefatos para qualquer geração paga.

[Manual de execução pelo Work](docs/PIXELLAB-WORK.md).

## Cenários e móveis PixelLab para o Pixel Studio

Além dos personagens, o projeto gera **3 salas (Rooms)** e **6 objetos independentes (Objects)** usando a API PixelLab. Um inventário gratuito confere duplicatas antes de cada chamada paga. A criação é dividida em dois workflows autorizados, com relatórios e possíveis PNGs temporários em artifacts; os recursos permanecem na biblioteca PixelLab.

[Ver catálogo, execução e cuidados](docs/PIXELLAB-OFFICE.md).

## Primeiro teste (sem custo de IA e sem upload)

Requisito: Python 3.12+.

```bash
python -m unittest discover -s tests -v
python -m videoforge.pipeline --video canal/alchemy-lab/videos/teste-10s/video.json --output output/storyboard.json
```

A ação **Actions > Validar VideoForge AI** também roda os testes e salva o storyboard de 10 segundos como artifact. Isso **não** produz um vídeo.

## Próximas entregas

- Gerar roteiro, imagem de referência, personagens/cenários/objetos transparentes e animação por camadas.
- Gerar voz, mixagem e MP4 com FFmpeg.
- Validar o primeiro vídeo de 10 segundos.
- Fazer upload **privado** de teste, depois automatizar o agendamento.

## Segurança

Não adicione chaves de API, tokens OAuth nem mídias privadas no Git. Armazene credenciais em GitHub Actions Secrets; use limites de custo e prevenção contra duplicatas.

**Nome do produto:** VideoForge AI. **Nome atual do repositório:** `video-forte-ia`.

## Regra permanente de entrega e publicação do painel

Sempre que modificar a interface do escritório, os agentes ou as configurações de canais que o painel utiliza, **não concluir a tarefa apenas com os arquivos no repositório**: executar a validação, permitir o deploy automático do Pages, conferir o resultado da execução e informar o link publicado quando confirmado. Se a publicação falhar ou depender de acesso/configuração indisponível, informar claramente o bloqueio e oferecer o próximo passo. Nunca afirmar que a página está online sem evidência do GitHub.

## Sprites reais PixelLab no escritório virtual

Os **9 PNGs aprovados** das salas/objetos foram incorporados ao repositório em `site/assets/pixellab/`. O Canvas do `site/` carrega as imagens localmente e usa o novo modo PixelLab como padrão após o carregamento; um botão alterna para o layout desenhado originalmente. O minimapa e a seleção dos agentes acompanham a disposição ativa. As animações de personagens permanecem guardadas na biblioteca PixelLab e ainda serão integradas separadamente.

Mais detalhes: [guia do escritório](site/README.md).

## Animações do Alex no Pixel Studio

A integração de agentes agora usa as **48 combinações de seis movimentos e oito direções** exportadas do PixelLab, comprimidas em **seis atlas PNG** com quatro frames por direção. Os arquivos permanecem em `site/assets/pixellab/agents/alex/`; o `site/agent-animator.js` pré-carrega os atlas para desenhar diretamente no Canvas. O modo PixelLab aplica a animação coerente com o status real do agente e oferece um botão de prévia sem simular trabalho. Se algum arquivo faltar, preserva os avatars originais. Os oito agentes compartilham temporariamente o Alex.

## Navegação visual entre espaços do escritório

O módulo `site/agent-routines.js` acrescenta passeios demonstrativos manuais para os agentes: café, bebedouro, jogos, porta do banheiro e retorno ao posto. Usa a animação real `walk` do Alex e não altera os eventos de trabalho. Novos ambientes e ações sociais precisam ser gerados no PixelLab antes de substituir os marcadores por objetos reais. [Plano de animações e interações](docs/PLANO_INTERACOES_ESCRITORIO.md).

## Produtora com gerente, cinco departamentos e especialistas

O gerente humano entrega demandas ao diretor, que distribui por líderes de Editorial, Criação, Audiovisual e Qualidade, com **27 especializações planejadas**. O motor `videoforge/production/dispatcher.py` prepara **18 entregas** por vídeo, com dependências, incluindo título, descrição, tags, thumbnail, roteiro, voz, edição, QA e aprovação. Ainda **não executa IAs nem publica**: é a base segura para conectores futuros. O painel do escritório mostra a organização sem apresentar especialistas como online. [Guia da equipe](docs/EQUIPE_PRODUCAO.md).

Para animar conversas, reuniões e as especializações, o catálogo `personagens/alex/production-animations.json` define **137 ações**, das quais 122 são movimentos de personagem e 15 exigem sequências/objetos adicionais. [Controle de geração PixelLab](docs/PIXELLAB-PRODUTORA.md).


## Recepção automática de todas as imagens PixelLab

O workflow `.github/workflows/pixellab-production-import.yml` recebe, apenas por GET, os **sprites do Alex e os objetos animados** quando os lotes pagos terminam. Ele também pode ser executado manualmente para sincronizar imagens já existentes no PixelLab. Atlases completos são aceitos mesmo quando outros movimentos ainda estão processando, preservando versões anteriores; cada PNG tem tamanho e SHA-256 validados. O GitHub Pages atualiza automaticamente quando novos arquivos são commitados em `site/assets/pixellab/`. Não são iniciadas gerações, uploads de vídeos ou cobranças por esse recebedor.

Os seis atlas básicos, três cenários e seis objetos já aprovados permanecem intactos. A pasta `agents/alex/production/` recebe novos movimentos e `objects/production/` recebe spritesheets e prévias dos móveis, todos com manifests públicos saneados. Objetos novos ainda precisam de mapeamento de animações ao cenário; a recepção não significa que os objetos já estão animados na interface.

## Atualização: agentes animados e correção de cadeiras

O Pixel Studio utiliza agora movimentos profissionais por cargo via `site/agent-behavior.js`, com demonstração opcional pelo botão 🎬 e conversas sincronizadas pela sala criativa. Os oito assentos PixelLab foram alinhados às cadeiras e as placas estão mais compactas. Os estados reais continuam vindo exclusivamente do backend, sem simular execução de IAs. Mais detalhes em [docs/CORRECOES_AGENTS.md](docs/CORRECOES_AGENTS.md).

### Caminhada mais suave no escritório

A movimentação das rotas demonstrativas agora é calculada a 112 px/s, com quadros de `walk` baseados na distância e redesenho de até 30 FPS enquanto os agents caminham. As curvas são graduais e o sprite não gira automaticamente para sul quando para. Nenhuma nova geração PixelLab nem atividade falsa de agentes é iniciada. Ver `site/README.md`.

## Atualização de caminhada do Alex

O utilitário `scripts/refresh_pixellab_walk.py` aceita por GET a exportação do PixelLab e só substitui `site/assets/pixellab/agents/alex/walk.png` quando há uma variante nova completa (8 direções, 4 frames, 88×88 RGBA, personagem aprovado) ou uma versão atualizada de `walk`. Atualiza o SHA-256 do manifesto. Se faltar quadro ou o conteúdo for igual, mantém o anterior. Os agentes continuam usando o nome lógico `walk`, então a troca alcança todos os trajetos, sem alterar os status reais nem iniciar geração paga. O workflow `pixellab-walk-upgrade.yml` faz a sincronização e publica Pages somente após substituição verificada.


### Walking PixMinimax com 8 frames por direção (10/11/2026)

A captura fornecida confirmou 8 quadros por direção em `walking`. O atlas básico `walk.png` deve usar 8×8 frames (704×704 px) quando houver os 64 PNGs completos no ZIP PixelLab. A propriedade `motions.walk.frames=8` e a largura `704` substituem o antigo pressuposto de 4 frames; os outros cinco movimentos básicos continuam com 4 quadros. O Canvas detecta a contagem por movimento e as rotinas mantêm o mesmo comprimento de ciclo de caminhada (56 px), usando passos de 7 px com 8 frames. Exportações incompletas não substituem o último atlas validado. O workflow de atualização faz apenas GET, executa testes e publica Pages quando um atlas novo é realmente versionado. Não altera estados reais dos agentes e não gera novas imagens pagas.


## Integração dos movimentos extras no Pixel Studio

`site/agent-interactions.js` coreogra as demonstrações de café, água, jogos, entrada do banheiro e retorno à cadeira, usando os sprites de personagem disponíveis. `site/agent-routines.js` toca os movimentos após o trajeto (passos da animação `walking` mantidos durante a caminhada) e alterna ações por duração. Todas essas atividades são **demonstração visual**, nunca confirmação de trabalho real, nem geram chamadas pagas.

As 12 ações compostas do catálogo estão mapeadas; `use_elevator` permanece bloqueada porque não existe elevador real no cenário. As 3 animações de objetos exigem sprites próprios e revisão visual: a biblioteca atual só inclui a cadeira sem movimentos rotulados e o armário ainda não foi recebido. Não divulgar essas três como prontas.

Os 122 sprites de personagem importados aparecem em galerias distribuídas pelos oito cargos (categorias profissionais, sociais, lazer e pausas). A seleção no painel permite testar manualmente qualquer animação da biblioteca. O modo 🎬 acrescenta emoções e descanso visual nas estações; status real e execução de vídeos não são inferidos dos sprites. O carregador busca apenas os PNGs necessários a cada momento, com proteção contra downloads duplicados. Testes: `tests/test_agent_interactions.js`, `tests/test_agent_routines.js`, `tests/test_agent_behavior.js`.


## Correção de cenário e diagnóstico de IA — novembro/2026

O cenário PixelLab foi reorganizado em 3 salas aprovadas (produção, criação e laboratório) e 3 ambientes **visuais em prévia** (copa com água, sala de jogos, WC). O catálogo isolado de objetos foi substituído por móveis contextualizados nas salas e circulação inferior, com sinalização. O layout e os destinos usam agora `site/office-map.js` como fonte de coordenadas compartilhadas, consumida por `office-art.js` e `agent-routines.js`. Os oito funcionários ganharam marcadores de profissão distintos e as sequências de interação respeitam os frames de gestos (em vez de ignorar o relógio da rotina). Nenhum sprite PixelLab pago foi regenerado.

Os oito agentes do cadastro em `agentes/equipe.json` seguem sem `modelo_ia` e com `habilitado: false`. O exportador `scripts/build_dashboard_data.py` agora adiciona diagnóstico **sem segredos** para cada papel: modelo definido, executor habilitado, dependências e existência de eventos. O painel identifica expressamente quando a IA não está ligada. O exportador valida que as dependências referenciam agentes existentes, não formam ciclos, e recusa marcar agentes sem executor/modelo como `trabalhando`, `revisao` ou `concluido` por simples relatório. **Isso melhora a integridade, mas não conecta uma API nem autoriza gastos.** Para IA real, ainda são necessários executores backend, credenciais protegidas, modelos por cargo, limites de custo e evidências de tarefas reais.

## Agência unificada gerada com o PixelLab

O novo gerador `videoforge/pixellab/agency_scene.py` aceita a imagem de referência reduzida do cenário aprovado e solicita **uma imagem ampla 688×384** via `/generate-image-v2` no PixelLab. Há uma ação dedicada [PixelLab — Gerar agência unificada](.github/workflows/pixellab-agency-scene.yml) com `plan` (gratuito) e `generate` (manual e sujeito a confirmação explícita de créditos e visibilidade dos artifacts). A cena produzida **não é publicada automaticamente**: é necessário baixar o PNG, revisá-lo, depois integrar a arte e recalibrar os oito postos, rotas e minimapa. O site atual permanece intacto até isso acontecer. [Guia completo](docs/PIXELLAB-AGENCIA-UNIFICADA.md).

## PixelLab — sede única integrada ao Canvas

O panorama real `site/assets/pixellab/scenes/agencia-unificada.png` foi gerado pela API PixelLab v2 (workflow #43039103117) e importado com hash/dimensões verificados. O Canvas utiliza essa imagem como planta **contínua de um único escritório**, com oito agentes animados, rótulos, minimapa e rotas configuradas em `site/office-map.js`. Permanecem disponíveis os assets anteriores para fallback; a mudança de cenário não executa agentes nem altera publicação dos vídeos. Mais detalhes em `site/README.md` e `docs/ESCRITORIO_AGENTES.md`.

## Codex Proxy no backend — 22 rotas preparadas

O VideoForge já dispõe do cliente de integração [Codex Proxy](videoforge/proxy/client.py)
com todas as 22 rotas do servidor Go fixado e suporte a texto, Responses,
ferramentas, imagens (geração e edições), Anthropic, streaming, catálogo de
modelos, múltiplas contas e administração. A integração **não consome IA
automaticamente**: os agentes continuam sem executor habilitado no Pages.
O planejamento do gerente agora anexa as capacidades de backend às 18
entregas, sem executar chamadas.

- **Testar sem credenciais:** `python -m unittest discover -s tests -p 'test_proxy_client.py' -v`
- **Inspecionar capacidades offline:** `python -m videoforge.proxy.cli --action catalog`
- **GitHub Actions:** `VideoForge - Codex Proxy backend` (modo offline,
  servidor Go com conta vazia e chave sintética; diagnóstico privado
  opt-in somente após proteger o Environment `proxy-runtime`).
- **Manual completo:** [docs/CODEX_PROXY.md](docs/CODEX_PROXY.md)

O GitHub Pages é estático e **não recebe tokens OAuth, API key nem acesso
direto ao proxy**. Chat em tempo real exige backend protegido com TLS; execução
por workflow pode ser feita sem hospedagem contínua, após configurar os
Secrets no novo repositório e implementar um executor autorizado com orçamento.
