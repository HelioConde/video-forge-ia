# Arquitetura proposta — VideoForge AI

## Handoff editorial cifrado entre agentes e briefing

A pesquisa de pauta por agentes exige agora dispatch manual do
proprietário em `main` (sem ativação por commit/push), uma chamada
autorizada e Environment `proxy-runtime`. O relatório contendo
candidatas e possíveis métricas YouTube é cifrado no runner via
`videoforge/channel_agents/secure_report.py` antes do artifact.
O briefing posterior só aceita artifact AES-256-GCM com AAD do run
e a mesma chave protegida; valida ainda seleção do Gerente,
auditoria do Subgerente, a aprovação humana e a reserva persistida.
Sem chave/credenciais ou modelo, bloqueia antes da geração.
[Contrato completo](PRIMEIRO_BRIEFING_AGENTES.md).
A proteção de dados não equivale a habilitar agentes visuais nem
desbloqueia o HTTP 429.


## Isolamento do ambiente OAuth na triagem de pesquisas

A análise opcional `youtube-readonly` de
`external-research-validation.yml` utiliza o Environment protegido
`youtube-analytics-readonly`, **idêntico ao workflow de gerentes**.
A triagem **não** depende dos Secrets do Codex Proxy em
`proxy-runtime` e falha antes de solicitar OAuth se estiver sem
`YOUTUBE_CLIENT_JSON` ou `YOUTUBE_OTAKU_BR_TOKEN_JSON`.
Somente `workflow_dispatch` explícito na `main`, sem retrigger,
pode acessar os dados privados; PR e push executam apenas testes.
O relatório com métricas continua no runner temporário, sem artifact.

## Exportação segura da fila de pesquisas ao escritório

O `build_dashboard_data.py` projeta o último pacote de pesquisa pública
validado para `canais[].pesquisa_externa`: apenas fontes e perguntas
editoriais, sem identificador YouTube, métricas de desempenho, OAuth,
indicadores de popularidade ou aprovações falsas. URLs são saneadas antes
da publicação, com parâmetros removidos. A aba Canais do escritório
exibe os sinais em cartões de fonte, sem marcar nenhum agente como
`trabalhando`. Sem pacote validado, não há fila; uma entrada inválida
bloqueia o build, em vez de exibir fato ou ranking fictício.
O uso de uma pesquisa pública não resolve HTTP 429 do Codex Proxy.

## Diagnóstico privado de cota sem chamada generativa

`videoforge/proxy/quota_diagnostic.py` resume a elegibilidade de conta
e as janelas de uso relatadas pelo endpoint administrativo do proxy
fixado, sem imprimir identificador, assinatura, saldo, token, porcentagens
exatas ou corpo do erro upstream. `cli.py --action quota` tem modo
`cached` local e `live` (até um GET externo, manual e autorizado).
`codex-proxy-backend.yml` inclui a opção de dispatch
`private-quota-live` no `proxy-runtime`, com `run_attempt=1` e
sem endpoints de geração. Sinais de limite não provam isoladamente
a causa do erro anterior; ausência deles não comprova quota disponível.
[Documentação](PROXY_QUOTA_DIAGNOSTIC.md).

## Entrada de inteligência editorial externa

O assistente pesquisa fatos públicos e documenta fontes em JSONs datados dentro
de `canal/<id>/editorial/pesquisas/`. O módulo sem rede
`videoforge/channel_agents/external_research.py` valida o formato e o canal.
`team.py` entrega o registro mais recente a `ideation.py` apenas como
**contexto com fontes**; não substitui o pesquisador real, o inventário completo
de vídeos, a API YouTube Analytics, a auditoria do Subgerente ou o ranking do
Gerente. O fluxo não ativa o Proxy, a mídia nem o upload em resposta a commits
de pesquisa. Sem IA disponível (ex.: HTTP 429), o material permanece aguardando
próxima execução autorizada; nenhum papel visual é marcado como trabalhando.
Consultar [protocolo da pesquisa externa](PESQUISA_EXTERNA_VIDEOFORGE.md).

### Conferência de contexto sem modelo de IA

O módulo `research_triage.py` é uma triagem **não generativa** de
correspondências explícitas entre aliases das séries no pacote de pesquisa
e títulos públicos contidos em um snapshot autenticado do YouTube. Confere
`history_complete`, `read_only`, identidade, origem e campos de métricas,
mas não produz ideias, classificações de desempenho ou decisões.
O workflow de validação externa possui opção manual `youtube-readonly`,
usando somente as credenciais YouTube do Environment `proxy-runtime`:
retém dados privados apenas no runner e não publica Analytics, não gera
check de trabalho autônomo, não gera mídia e não toca no Proxy com HTTP 429.
A triagem de palavras não substitui deduplicação semântica nem aprovação.
[Contrato](PESQUISA_EXTERNA_VIDEOFORGE.md).

## Telemetria das etapas reais dos agentes visuais

O VideoForge chama `role_task()` durante tarefas reais de roteiro/validação, voz, imagem, animação/composição, renderização e QA. `videoforge/production/role_events.py` envia eventos de início/conclusão do estágio por GitHub Checks e por GitHub Commit Status (fallback). Ambos publicam somente identificadores de função/canal, estado e link verificável do workflow; nenhum prompt, conteúdo de vídeo, token ou OAuth é publicado. A interface read-only em `site/office-live.js` procura o último run ativo de AutoEditor/Editorial, confere a identidade do registro e associa `trabalhando` ao papel correspondente. A etapa de edição só marca Editor enquanto **a renderização estiver efetivamente em execução**; conclusão do GitHub run nunca deixa o funcionário ativo. Se ambos os canais de telemetria estiverem indisponíveis, somente o pipeline global é sinalizado, sem atribuição fictícia a funcionários. Atualização via polling: não é streaming em tempo real.

## Idempotência persistente entre execuções

`videoforge/production/attempt_claim.py` registra uma tentativa de briefing usando `PUT /contents/` da API GitHub sem `sha` de substituição. O arquivo é único por hash SHA-256 do canal + anime + título + ângulo, e só contém metadados públicos saneados (não resposta, token ou prompt). Se já existir, ou se a gravação não puder ser confirmada, falha antes da chamada ao Codex Proxy. O workflow manual é serializado por concurrency group; o job real usa `contents:write` apenas para a reserva. O artefato de resposta continua cifrado e depende de revisão independente. A trava não cobre alterações semânticas nas pautas nem substitui auditoria de consumo por conta. Consulte [manual](PRIMEIRO_BRIEFING_AGENTES.md).

## Handoff editorial e primeiro briefing protegido

`videoforge/production/editorial_handoff.py` valida a decisão real da equipe do canal, a auditoria do Subgerente, a política do canal e a reserva humana previamente persistida. O workflow `.github/workflows/agent-one-briefing.yml` inicia em modo offline; o modo de uma chamada real exige branch main, autoria do proprietário, confirmação humana, Environment protegido e modelo disponível no Codex Proxy. A saída privada é criptografada por `videoforge/production/secure_draft.py` com AES-256-GCM antes de virar artifact do Actions. A tarefa ainda aguarda QA e não é considerada `done`. O registro de reservas ainda não implementa lock global entre workflow runs, portanto a repetição entre runs continua exigindo cuidado e autorizações separadas. Ver [manual](PRIMEIRO_BRIEFING_AGENTES.md).

## Despacho de agentes de texto pelo Codex Proxy

`videoforge/production/agent_dispatch.py` conecta as etapas textuais elegíveis do DAG do `dispatcher.py` aos especialistas do `agentes/equipe.json` por `videoforge/proxy/agent_gateway.py`. A prévia `plan_text_dispatch` não consulta modelos nem cobra cotas. Somente um runner backend confiável com aprovação por execução pode chamar `run_text_draft`, que reserva a tarefa de modo exclusivo e salva um rascunho privado com hash para revisão independente, sem atualizar o DAG como concluído. O workflow `production-request.yml` exibe somente a prévia; publicação e geração paga não são habilitadas. Ver [guia](AGENT_TEXT_DISPATCH.md).


## Remotion — movimentos de sprites baseados no Fofinho Parte 3

A autoria de movimento fica no `motion_plan` validado por `videoforge/production/motion_plan.py`, com referências a IDs reais do `layer_plan`. O Artista usa `character_parts` somente quando se pretende movimentar uma patinha/mão separadamente, removendo-a do corpo-base durante a extração; cada PNG adicional entra no orçamento de imagens. O módulo puro TypeScript `videoforge/motion/videoforge-motion.ts` implementa transformações 2D determinísticas (`paw-lift`, `paw-wave`, `pat`, `hop`, `rise`, `fall`, `orbit`, `float` etc.), sem rigging 3D nem deformação de corpo inteiro. `videoforge/motion/remotion_overlay.py` verifica âncoras do `master-short.tsx` da versão pinada do AutoEditorVideo e o instrumenta somente no checkout temporário, preservando suporte anterior a camadas estáticas quando não há motion plan. O Animador registra `qa-motion.json` e hash da ferramenta, depois o Editor renderiza. Revisão visual humana continua obrigatória. Os 18 trechos da Parte 3 estão preservados em um blueprint **plan-only** para futuras cenas oficiais e narração, sem inferir que o aplicativo já produziu esse capítulo. [Detalhes](FOFINHO_PARTE3_MOTION_REMOTION.md).

## Regra 2 — decomposição per-scene em camadas reais

O módulo `videoforge/production/scene_layers.py` valida o storyboard de personagens e props por cena e deriva as camadas **exclusivamente por edição da própria imagem-mãe** com Codex Proxy. O background é uma reconstrução opaca sem sujeitos independentes; personagens e objetos móveis são PNG RGBA 720×1280 com alfa não trivial, coordenadas preservadas por contrato e SHA-256 vinculado à imagem-mãe. Cenas sem elementos móveis reutilizam o master. O procedimento verifica bytes, hashes, limites de custo, papel do agente e integridade geométrica; sem tentar mascarar com código o que o provider falhou em extrair.

O ilustrador armazena `scene-layers.json`, o revisor independente de etapa gera `qa-camadas.json`, o animador monta `remotion-props.json` com `renderMode=multilayer` e o Editor executa Remotion. São tarefas distintas marcadas por `role_task`; nenhum evento significa ativação de agentes autônomos. O formato é suportado pelo Remotion já pinado em AutoEditorVideo. Os props `hero_prop` ficam estáticos no engine atual, ainda que separados para futura animação; não afirmar rigging já implementado. Estética, encaixe perfeito, ausência de fantasmas e direitos continuam exigindo QA humano antes de publicar. Cota exata é pré-autorizada, sem retries nem fallback. [Guia detalhado](CAMADAS_CENA_MESTRE.md).

## Âncora visual obrigatória e direção de arte do VideoForge

O fluxo de imagem do próprio VideoForge resolve a referência aprovada do canal em `canal/<id>/referencias/<arquivo>` (se configurada em `visual_lock.reference_path`). Sem referência, o worker gera **uma única imagem âncora** usando `gpt-image-2` no Codex Proxy; todas as demais cenas são derivações usando `ProxyClient.images_edit_files` e a **mesma imagem 1** como entrada de referência. Assim, uma falha no modelo de edição bloqueia a tarefa: não há fallback para oito gerações independentes. A bíblia visual fica no manifesto e é validada antes de gastar cotas.

O módulo `videoforge/production/visual_lock.py` valida identidade, estilo por vídeo, caminho da referência, prompts e hashes da cadeia de edição. `imagens.json` registra o SHA-256 da bíblia e da imagem original; `qa-imagens.json` diferencia a prova técnica de referência da **continuidade visual efetivamente revisada**. A produção técnica de prévia continua possível, mas a aprovação artística e o upload permanecem bloqueados até revisão visual independente. É proibido substituir esse fluxo por arte gerada no chat.

## Executor AutoEditorVideo: motor técnico reutilizável

O novo perfil `geradores/autoeditor/gerador.json` é genérico e
reaproveitável por qualquer canal, em paralelo aos geradores de
anime/kids/dorama e aos modelos técnicos estáticos/animados.
O executor `videoforge/generators/autoeditor.py` integra o
renderizador real `AutoEditorVideo/motion-remotion/ArquivoOtakuMaster`
**pinado por commit** com narração Edge TTS marcada por palavra,
imagens reais via Codex Proxy e inspeção FFprobe + SHA-256.

O planejamento é offline e livre de quota, enquanto a renderização
é opt-in com autorização manual e Environment protegido.
Os agentes fornecem os dados de roteiro, pesquisa e storyboard;
o motor não falsifica histórico YouTube, não gera artes via código,
não repete requisições HTTP 429 automaticamente e não faz upload.

[Manual AutoEditor](../geradores/autoeditor/README.md).

## Catálogo aberto de geradores especializados

**Gerador de vídeo** não é uma categoria fixa: cada pasta
`geradores/<slug>/gerador.json` possui sua própria sequência de trabalho
(DAG), perfil editorial, direção visual e responsabilidades dos agentes.
A descoberta é automática pelo módulo
`videoforge/generators/registry.py`, sem lista pré-definida de nichos.
Os exemplos iniciais são anime, infantil (kids) e dorama, mas é possível
adicionar qualquer outro formato sem modificar o catálogo.

**Compatibilidade:** os modelos técnicos de produção em `modelos/`
continuam existindo. O canal escolhe opcionalmente `gerador_padrao`,
e o vídeo pode escolher `gerador` e sobrescrever o canal. Uma escolha
de gerador não altera automaticamente `modelo` ou `modelo_padrao`.

**Segurança:** o catálogo é apenas declarativo; não carrega código
arbitrário nem executa IA, mídia ou uploads. Cada executor real precisa
ser integrado e validado em um workflow separado. Os perfis não podem
desligar a regra global de imagens exclusivamente produzidas pelo
gerador integrado, a revisão de qualidade ou a aprovação humana.

Documentação completa: [geradores/README.md](../geradores/README.md).

## Organização por canal e por modelo

```text
canal/
  <canal-id>/
    canal.json
    videos/
      <video-id>/
        video.json
modelos/
  <modelo-id>/
    modelo.json
videoforge/
  config.py     # resolve a receita do canal/vídeo
  pipeline.py   # prepara e valida storyboard (dry-run)
tests/
.github/workflows/
output/         # gerados localmente, fora do Git
```

- **Canal**: define idioma, configurações de publicação e `modelo_padrao`.
- **Vídeo**: guarda duração, roteiro/cenas e `modelo` opcional. Quando existe, substitui o modelo padrão do canal.
- **Modelo de produção**: receita independente do canal para etapas de roteiro, imagem, animação, voz e montagem.
- **Modelo de IA**: provedor e identificação configuráveis para cada etapa (`provedor` e `modelo_ia`), ainda não integrados.

## Padrão obrigatório de organização e manutenção contínua

**Regra permanente: toda implementação, manutenção, correção, experimento ou refatoração deve deixar o projeto organizado.** Nenhuma funcionalidade deve ser considerada concluída se introduzir desordem estrutural, duplicação desnecessária ou documentação desatualizada.

### Responsabilidades por local

| Caminho | Responsabilidade |
| --- | --- |
| `canal/<id>/canal.json` | Configurações próprias do canal e modelo padrão |
| `canal/<id>/videos/<id>/video.json` | Definição de cada vídeo e seleção opcional de modelo |
| `modelos/<id>/modelo.json` | Receitas reutilizáveis de produção e opções de IA |
| `videoforge/` | Código reutilizável de orquestração, configuração e módulos de produção |
| `tests/` | Testes correspondentes aos comportamentos implementados |
| `.github/workflows/` | Pipelines de CI e agendamento, sem lógica de negócio duplicada |
| `docs/` | Documentação de arquitetura, decisões e procedimentos |
| `output/` | Saídas geradas, logs e mídias locais; conteúdo não versionado |

### Checklist obrigatório para cada mudança

1. **Antes:** inspecionar os diretórios e os módulos afetados; aproveitar os componentes existentes antes de criar outros.
2. **Durante:** colocar cada arquivo na pasta de sua responsabilidade, manter nomes claros, funções coesas e interfaces estáveis.
3. **Isolamento:** não misturar configurações, assets nem credenciais entre canais; herança de modelo por vídeo precisa continuar funcionando.
4. **Limpeza:** evitar arquivos descartáveis ou duplicados; só apagar conteúdo após confirmar que não é utilizado.
5. **Depois:** atualizar README/documentação e exemplos quando houver mudança de comportamento, executar testes e inspecionar a estrutura final.
6. **Integração:** manter os workflows organizados e validar que automações novas não substituam ou quebrem as existentes.

As regras também estão resumidas no [README principal](../README.md) e devem ser seguidas por agentes conforme [AGENTS.md](../AGENTS.md).

## Catálogo de canais herdado do AutoEditorVideo

| Pasta | Chave legada | Modelo inicial |
| --- | --- | --- |
| `canal/otaku-br/` | `br` | `camadas-animadas` |
| `canal/otaku-en/` | `en` | `imagem-estatica` |
| `canal/gamer/` | `games` | `imagem-estatica` |
| `canal/manu-kids/` | `kids` | `camadas-animadas` |
| `canal/alchemy-lab/` | `alchemy` | `imagem-estatica` |

Os padrões são provisórios. Os arquivos em `arquivo-editorial/` são referências e não scripts de publicação. O teste de 10 segundos agora fica em `canal/alchemy-lab/videos/teste-10s/`.

Consulte [MIGRACAO_AUTOEDITORVIDEO.md](MIGRACAO_AUTOEDITORVIDEO.md). Nenhum token ou upload foi migrado.

## Meta

Automatizar: pauta > roteiro > planejamento de cenas > geração de imagens e camadas > animação > narração > montagem > validação > upload no YouTube.

## Módulos planejados

1. **Content Planner**: tema, canal, vídeo, roteiro, storyboard e continuidade dos personagens.
2. **Scene Composer**: imagem completa de referência; extração de cenário, personagens e objetos transparentes.
3. **Animator**: anima os elementos separadamente, preservando enquadramento e identidade.
4. **Audio Studio**: vozes e efeitos licenciados, com sincronização.
5. **Renderer**: renderização FFmpeg com legendas e áudio.
6. **Quality Gate**: duração, consistência, assets ausentes e duplicatas.
7. **YouTube Publisher**: OAuth/YouTube Data API, teste privado antes de liberar publicação.
8. **Scheduler / Observability**: GitHub Actions, logs, recuperações e status de cada canal.

## Etapas de entrega

- [x] Organização de pastas por canal, vídeo e modelo reutilizável.
- [x] Herança de modelo do canal com sobrescrita por vídeo, com testes.
- [x] Storyboard JSON de exemplo e validação no GitHub Actions.
- [ ] Integração real de IA para roteiros, imagens, animação e voz.
- [ ] Renderização de um MP4 de 10 segundos.
- [ ] Upload privado de teste no YouTube.
- [ ] Agendamento automático e monitoramento.

## Segurança e limites atuais

- O protótipo **não gera imagens, áudio ou MP4 e não realiza uploads**.
- Credenciais devem ficar em Actions Secrets, nunca em `canal/` ou `modelos/`.
- Testar em privado primeiro, impedir uploads repetidos, validar qualidade e controlar custo das APIs.

## Estrutura do escritório Pixel Studio

O frontend estático é organizado em `site/`:

- `office-art.js`: desenho original do estúdio e dos personagens, com dados de posição reutilizados pela interação.
- `office-renderer.js`: engine Canvas 2D, câmera, zoom, gestos de toque, hit-testing e minimapa.
- `app.js`: seleção, detalhes dos agentes/canais e consumo seguro do snapshot de status.
- `styles.css` e `index.html`: disposição responsiva, HUD e painéis.
- `data/status.json`: snapshot público gerado pelo backend, sem credenciais.

Os arquivos de arte não executam serviços de IA. A publicação da interface ocorre por GitHub Pages Actions e é independente da publicação de vídeos no YouTube.

## Integração opcional PixelLab

- `personagens/<slug>/profile.json`: descrição e animações próprias de cada personagem.
- `videoforge/pixellab/client.py`: autenticação, APIs PixelLab v2, jobs e exportações.
- `videoforge/pixellab/cli.py`: seleção da base existente ou criação, animações e planejamento seguro.
- `.github/workflows/pixellab-character.yml`: comando manual com controle de custos e divulgação.
- `tests/test_pixellab.py`: testes simulados sem rede.
- `output/pixellab/`: arquivos temporários fora do Git.

A geração de sprites ainda não está conectada ao Canvas nem ao renderizador dos vídeos. Veja `docs/PIXELLAB.md`.

## Orquestração PixelLab em lote para Work

- `videoforge/pixellab/batch.py`: consulta GET a base exata, compara movimentos/direções, reutiliza grupo anterior por ID, limita novas gerações e escreve relatório público sem UUID.
- `.github/workflows/pixellab-work.yml`: workflow manual para o ChatGPT Work, com modos planejar/gerar, autorização de custo/exposição, trava `pixellab-personagens` e máximo de oito POSTs por disparo.
- `tests/test_pixellab_batch.py`: simulações sem API paga, cobrindo reuso, antduplicação, bloqueios e exportações.
- `docs/PIXELLAB-WORK.md`: operação, parâmetros e procedimento de retomada segura.

A fonte de verdade dos movimentos continua sendo a conta PixelLab; o GitHub armazena apenas relatório de execução e ZIPs opcionais por sete dias, nunca segredos ou mídias geradas permanentemente no Git.

## Cenários e objetos do Pixel Studio gerados no PixelLab

O catálogo `cenarios/escritorio/pixellab-plan.json` descreve três salas e seis objetos em paleta coerente. O módulo `videoforge/pixellab/office_assets.py` faz auditoria paginada, controla custos por limite de POSTs, salva status saneado e exporta PNGs quando URLs de prévia confiáveis estiverem disponíveis. As bibliotecas Rooms e Objects do PixelLab são fonte de verdade; não criar mídia versionada.

Workflows: `pixellab-office-audit.yml` (somente GET), `pixellab-office-start.yml` (uma sala e dois objetos), `pixellab-office-continue.yml` (duas salas e quatro objetos, condicionado ao sucesso do primeiro). Validar com `tests/test_pixellab_office.py`. Arte visual só é ligada ao Canvas após inspeção das imagens. Ver `docs/PIXELLAB-OFFICE.md`.

## Publicação dos sprites PixelLab para o Canvas

As nove imagens aprovadas foram copiadas dos artifacts das Actions para `site/assets/pixellab/` em um único importador com validação de PNG, dimensões, hash e ausência de dados de conta. O manifesto local registra `sha256`, sem IDs ou URLs privadas de PixelLab. O desenho de cenas no Canvas continua concentrado em `site/office-art.js`; o renderizador `site/office-renderer.js` só controla carregamento/viewport/seleção, e `site/app.js` controla o botão de modo. Falhas de carga preservam a arte anterior. O site é estático e não chama PixelLab em tempo de execução.

## Animação de agentes a partir dos sprites do PixelLab

O workflow `.github/workflows/pixellab-export-alex.yml` exporta os frames sem gerar novamente; `scripts/import_pixellab_agents.py` converte o ZIP validado em atlas PNG, eliminando todos os metadados privados; a action `.github/workflows/pixellab-import-alex.yml` salva os arquivos no repositório. O manifesto `site/assets/pixellab/agents/alex/manifest.json` guarda apenas direções, movimentos, dimensões e hashes. O carregador `site/agent-animator.js` valida seis atlas de 352×704 e desenha sincronicamente no Canvas com suporte a `prefers-reduced-motion`. `site/office-art.js` faz a seleção de animação por status backend e `site/office-renderer.js` mantém apenas câmera, render e hit-testing. Falha ao importar qualquer atlas não impede a arte anterior.

## Locomoção visual e interação com cenários

`site/agent-routines.js` mantém somente rotas de demonstração em memória do navegador. A biblioteca de destinos limita as ações a café, água, jogos, entrada do banheiro e retorno à estação; não altera `status` do backend, não faz solicitações à API PixelLab e não exibe consumo de recursos inexistentes. O Canvas `office-art.js` utiliza a mesma posição/direção calculada para `walk` e `idle`, `office-renderer.js` aplica o mesmo deslocamento a hit-testing e minimapa, e `app.js` oferece comandos explicitamente rotulados como prévia. Não confundir com robôs operacionais ou uma simulação persistente de trabalho.

## Gestão, delegação e novas animações da produtora

`agentes/equipe.json` v2 preserva oito cargos visuais e acrescenta estrutura hierárquica (`manager`, `departamentos`, especialistas lógicos desativados). O exportador `scripts/build_dashboard_data.py` publica apenas contagens e nomes de departamentos como `organizacao`. No painel, as relações são marcadas como planejadas; não inventar execução real.

`videoforge/production/dispatcher.py` cria o DAG de 18 tarefas por demanda; as atividades são apenas `blocked` ou `ready` até haver artefato validado. Não executa IA/pagamento/publicação. `personagens/alex/production-animations.json` contém 137 ações categorizadas em `character`, `sequence` e `object`. O motor `videoforge/pixellab/production_animations.py` só paga por direções de personagem ausentes após verificar GET e autorização, sem guardar IDs privados nos artefatos; novos sprites precisarão de revisão visual antes de entrar no Canvas.

### Atlas extras da produtora e carregamento tardio

A action `pixellab-production-import.yml` transforma a exportação do PixelLab em atlases PNG e manifesto de produção, sem UUIDs. O carregador do Canvas lê o manifesto como recurso opcional e só busca a animação escolhida pelo usuário; nenhuma animação nova é simulada enquanto o arquivo não estiver presente. Os seis atlas originais e o fallback anterior permanecem inalterados. Os movimentos extras são usados apenas como **prévia visual** até os eventos reais dos especialistas serem conectados.


## Recepção incremental e versionamento das imagens PixelLab

O workflow de importação `.github/workflows/pixellab-production-import.yml` é acionado após a conclusão dos lotes PixelLab de personagens e objetos (inclusive em caso de falha de geração, para aproveitar sprites completos), ou por `workflow_dispatch`. Ele usa **somente GET** e armazenamento temporário para os ZIPs; nenhuma mídia bruta, UUID, prompt, token, URL assinada ou metadado privado é commitado. A mesma trava de concorrência da recepção serializa as alterações no Git.

`scripts/import_pixellab_production.py` recebe os frames do Alex, confere a identidade do personagem, valida PNGs RGBA de 88×88, monta spritesheets de quatro quadros e preserva movimentos já importados quando a exportação nova está parcial. O manifesto público informa o total de movimentos disponíveis/pendentes.

`scripts/import_pixellab_objects.py` lê a biblioteca de objetos e o ZIP autenticado de spritesheet por meio de `PixelLabClient.download_object_spritesheet`. Somente os PNGs sanificados da cadeira e armário são versionados sob `site/assets/pixellab/objects/production/`. URLs e layouts originais da API não entram no site. Uma imagem de objeto importada não é interpretada como animação conectada até receber mapeamento visual/âncoras. `scripts/verify_pixellab_assets.py` confere assinaturas PNG, tamanhos, hashes e caminhos antes do commit. O trigger `site/**` do Pages realiza o deploy após cada alteração validada.


### Propagação confiável das imagens importadas ao Pages

O `GITHUB_TOKEN` não reativa workflows via `push` quando um próprio Actions faz commit. O recebedor possui saída `imagens_alteradas` e invoca a publicação via `workflow_call` somente se novos PNGs/manifests forem versionados. O workflow Pages é reutilizável e faz checkout explícito de `main` para publicar a revisão que contém as mídias aprovadas. Esta chamada não executa IA nem publica vídeos em canais.

## Movimentos profissionais e alinhamento de agents

O catálogo de animações especializadas é consumido pelo `site/agent-behavior.js` sem duplicação de nomes no renderizador. O Canvas seleciona as ações por cargo e status do backend; a prévia 🎬 permanece opt-in para funções não conectadas. `site/agent-routines.js` controla a demonstração de conversas e o deslocamento aos pontos da reunião. Slots e placas da sala PixelLab foram reposicionados e validados em `tests/test_office_layout.js`. Nenhuma chamada paga ou publicação de vídeos foi acionada. Consulte `docs/CORRECOES_AGENTS.md`.

### Passada e interpolação dos agents

O `site/agent-routines.js` retorna `poseFor(id, t)` com posição contínua, direção, distância acumulada e `frame` próprio para `walk`. Usa velocidade de 112 px/s, 14 px por troca de frame e curvas quadráticas curtas no corredor, sem modificar status reais. `hasMoving(t)` habilita o modo de 30 FPS em `site/office-renderer.js` apenas durante deslocamentos; `site/office-art.js` seleciona o quadro individual em vez de sincronizar todos os agents pelo relógio global. Mantêm-se os quatro frames existentes no PixelLab, sem novas chamadas pagas. Testes: `node tests/test_agent_routines.js`; CI do site e Playwright desktop/mobile.

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

## PixelLab — nova arte de sede única

O plano `cenarios/escritorio/agencia-unificada.json` e o pequeno PNG versionado em `cenarios/escritorio/referencias/` são entradas revisáveis para o módulo `videoforge/pixellab/agency_scene.py`, que reaproveita o cliente HTTP v2 existente. A API `generate-image-v2` é restrita a um único POST por execução manual; uma Action no branch da feature executa somente `plan`, não cobrança. O resultado é um artifact temporário; aprovação visual e importação no `site/assets/pixellab/scenes/` são processos separados, com os mapas de postos mantidos em `site/office-map.js`. Documentação: `docs/PIXELLAB-AGENCIA-UNIFICADA.md`.
