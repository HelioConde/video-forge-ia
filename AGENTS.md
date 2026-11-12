# AGENTS.md — Regras obrigatórias de manutenção do VideoForge AI

## Princípio permanente

Em **toda tarefa**, preservar e melhorar a organização do repositório. Antes de qualquer edição, leia `README.md` e `docs/ARQUITETURA.md`; mantenha esses documentos alinhados com o código.

## Estrutura por responsabilidade

- `canal/<id>/`: dados e opções de apenas um canal; vídeos em `videos/<id>/`.
- `modelos/<id>/`: modelo de produção independente, reutilizável entre canais ou sobrescrito por vídeo.
- `videoforge/`: código da aplicação modular; não colocar toda a lógica em um só arquivo.
- `tests/`: testes do comportamento alterado.
- `.github/workflows/`: orquestração da CI; não duplicar a lógica de aplicação.
- `docs/`: regras, decisões arquiteturais e documentação.
- `output/`: arquivos e mídia gerados, não versionados.

## Em toda mudança

1. Examinar caminhos e padrões existentes antes de criar algo novo.
2. Separar módulos por função e centralizar funcionalidades reutilizáveis; evitar duplicações e scripts auxiliares desnecessários.
3. Escolher nomes consistentes e manter isoladas as configurações de cada canal e vídeo.
4. Preservar o mecanismo de modelo padrão do canal e substituição opcional no vídeo.
5. Não adicionar segredos, tokens OAuth, mídias geradas ou logs ao Git.
6. Atualizar documentação e exemplos relevantes sempre que alterar contratos, caminhos ou comportamento.
7. Executar testes pertinentes e revisar o diff e a árvore de pastas antes de concluir.
8. Apagar arquivos somente após identificar referências e confirmar que não são mais necessários.
9. Se uma organização diferente for indispensável, documentar antes a razão e o impacto.
10. Não habilitar geração paga ou publicação real sem configuração e autorização explícitas.

**Critério de conclusão:** a tarefa deve funcionar e a aplicação deve continuar organizada, compreensível e sustentável para a próxima modificação.

## Escritório deve refletir trabalho real, nunca simulado

Toda execução real AutoEditor deve registrar no GitHub Checks as tarefas
efetivamente executadas por papel, por meio de
`videoforge/production/role_events.py`. Um check concluído exige
evidência local (arquivo real, integridade básica) e um check de erro
nunca pode ser apresentado como sucesso. A interface lê
`site/office-live.js` em modo somente leitura, validando ID, SHA,
canal e o vínculo com o workflow; nunca aceita eventos arbitrários.

**Não confundir uma etapa técnica automatizada com um agente IA
autônomo.** O modelo de IA de cada funcionário ainda não está
habilitado; os indicadores do escritório devem distinguir um
"executor de pipeline" de uma "IA independente". Nunca exibir
Publicador trabalhando sem upload autorizado/real e nunca pontuar
o Subgerente sem QA independente. Os registros ficam em GitHub
Checks para auditoria, sem prompts/tokens/dados privados.

O monitoramento do GitHub Pages é por polling, não por WebSocket, e
não consome cota do gerador de imagens. Não repetir uma produção para
testar a presença de animações no painel.

## Motor AutoEditorVideo dentro do VideoForge

O gerador `autoeditor` reutiliza somente o motor audiovisual
**Remotion MasterShort do repositório AutoEditorVideo fixado por SHA**,
narração Edge TTS WordBoundary, geração visual Codex Proxy e FFprobe.
É um backend técnico reutilizável para vários canais, não um novo
gerador separado para cada gênero; scripts editoriais são responsabilidade
dos agentes e gerentes do VideoForge.

Nunca importar ou disparar os uploaders legados, lotes diários,
publicadores ou rotinas históricas de manutenção do AutoEditorVideo.
`videoforge/generators/autoeditor.py` deve continuar independente de
credenciais YouTube. Somente render manual com autorização explícita,
Environment protegido `proxy-runtime`, sem repetições automáticas,
sem bypass de HTTP 429 e sem artes locais/assistente.

Se o TTS, as marcações, uma imagem de cena, o motor Remotion ou FFprobe
falharem, interromper a produção **sem gerar MP4 substituto**, sem
declarar QA editorial aprovado e sem upload. Manter roteiro, imagens
e backend separados das credenciais. Os testes offline em
`tests/test_autoeditor_generator.py` são obrigatórios.
Consultar [geradores/autoeditor/README.md](geradores/autoeditor/README.md).

## Arquitetura aberta para qualquer gerador de vídeo

Não manter uma lista fixa de geradores por gênero em código. Geradores
de vídeo são módulos declarativos independentes em
`geradores/<id>/gerador.json`, descobertos pelo catálogo
`videoforge/generators/registry.py`. Os exemplos `anime`, `kids` e
`dorama` **não são uma lista exaustiva**. Novos formatos devem ser
adicionados como manifestos de pipeline, com especialistas, dependências
e entregas próprias. Não forçar todos os nichos a usarem o mesmo roteiro,
a mesma animação ou a mesma direção artística.

Respeitar `video.json.gerador` > `canal.json.gerador_padrao`, ambos
opcionais. O gerador editorial e o `modelo` técnico são dimensões
independentes. Um cadastro não autoriza execução, cobrança, uso de
credenciais ou publicação. Conectar cada novo executor privado com
testes, verificação de saídas e orçamento limitado.

Nenhum módulo pode alterar a regra global: artes narrativas produzidas
exclusivamente pelo gerador de imagens integrado, sem desenhos de
substituição criados pelo assistente ou pelo código. QA e aprovação
humana são obrigatórios antes de publicar. Consultar
[geradores/README.md](geradores/README.md).

## Regras adicionais da migração

As pastas de canais reais são `otaku-br`, `otaku-en`, `gamer`, `manu-kids` e `alchemy-lab` dentro de `canal/`. A pasta fictícia `exemplo` foi removida. Não tratar `arquivo-editorial/` ou `conteudos/indice.json` como fila de produção. Não transportar workflows, segredos ou tokens do AutoEditorVideo. Consultar `docs/MIGRACAO_AUTOEDITORVIDEO.md` antes de modificar a migração.

## Regras do dashboard Pages

O escritório em `site/` deve ser organizado e consumir apenas snapshots públicos saneados gerados por `scripts/build_dashboard_data.py`. O navegador não roda agentes nem recebe tokens. Nunca exibir execução simulada como se fosse real; não copiar informações privadas para o Pages. Após a configuração do Pages pelo proprietário, a publicação é automática em mudanças relevantes da branch main e pode ser executada manualmente. O site publicado pode ser público mesmo com repositório privado; exportar apenas dados saneados. Consulte `docs/ESCRITORIO_AGENTES.md`.

**Cadastro de funcionários:** manter funções, dependências e identificação em `agentes/equipe.json`, sem duplicar a equipe em vários módulos. O painel deve consumi-lo por meio do exportador, nunca por leitura de arquivos privados no navegador.

## Política obrigatória de deploy do escritório

Em toda alteração relacionada a `site/`, `agentes/`, `canal/`, `scripts/build_dashboard_data.py` ou testes pertinentes, garantir que o workflow `.github/workflows/pages.yml` valide e publique o Pages automaticamente a partir da branch `main`. Verificar o status do workflow e a URL de deployment antes de comunicar sucesso; se falhar, diagnosticar e corrigir, sem encobrir erros. Não habilitar execução paga de IA ou publicação de vídeos no YouTube por causa do deploy do painel.

## Interface de escritório fullscreen

Em tarefas visuais, manter o desenho original do escritório exclusivamente em `site/office-art.js` e o motor Canvas 2D em `site/office-renderer.js`, com viewport responsivo; manter entrada HTML em `site/index.html`, estilos em `site/styles.css` e integração de dados em `site/app.js`. Manter controles operáveis por mouse/toque e evitar cartões que roubem a maior parte da tela. Não copiar assets proprietários do Pixel Agents; desenhos próprios são obrigatórios. Não inferir trabalho real de animações decorativas. Rodar `node --check` em `site/office-art.js`, `site/office-renderer.js` e `site/app.js` antes do deploy.

## Regra de revisão visual com captura

Para mudanças significativas em Canvas e CSS, renderizar a interface em um navegador, capturar desktop e celular, procurar falhas de proporção, áreas vazias, sobreposição de HUD e usabilidade por toque. Corrigir os problemas encontrados, executar os testes de CI e verificar o Pages após o deploy. Capturas locais são prévias visuais, não evidência automática de publicação em produção.

## Regra de design Pixel Studio

Não voltar a agrupar arte, navegação e integração de dados em um único script. O cenário pertence a `site/office-art.js`; o motor de render e interação pertence a `site/office-renderer.js`; o controlador de UI e snapshot pertence a `site/app.js`. Em celular, o minimapa deve ser recolhível e os elementos flutuantes não podem encobrir a equipe permanentemente. Validar sempre as capturas em desktop e celular após mudar a interface.

## PixelLab

Personagens são definidos em `personagens/<id>/profile.json`, API e CLI em `videoforge/pixellab/` e workflow em `.github/workflows/pixellab-character.yml`. Não inserir tokens ou UUIDs de personagens no código versionado. No repositório público, exigir consentimento de custo e exposição de artefatos. O padrão deve permanecer dry-run, sem cobranças automáticas. Não repetir POST pagos após timeout; consultar jobs anteriores. Ver `docs/PIXELLAB.md`.

## Lotes PixelLab acionados pelo Work

A execução em lote usa `videoforge/pixellab/batch.py` e `.github/workflows/pixellab-work.yml`. Antes de criar qualquer animação deve conferir o inventário do personagem exato selecionado por Secret, sem inferir qual dentre os 27 personagens é correto. Não recriar nem apagar a base, não publicar UUID ou token em relatórios, e não gerar movimentos/direções duplicados. Manter plano gratuito como padrão, limite máximo de 8 POSTs de animação por execução, duas autorizações explícitas para custos e exposição de resultados, e trava compartilhada de concorrência. Na presença de grupos desconhecidos ou dados incompletos, interromper em vez de adivinhar. Executar testes `tests/test_pixellab_batch.py` e ver `docs/PIXELLAB-WORK.md`.

## Geração PixelLab de cenários e objetos

Regras específicas em `docs/PIXELLAB-OFFICE.md`. Inventariar as bibliotecas Rooms e Objects antes de gerar; nomes estáveis `VideoForge AI - ... 2026`; não apagar nem recrear assets existentes; não publicar token, UUIDs ou URLs privadas. A produção autorizada foi organizada em primeiro lote (até três POSTs) e continuação após sucesso (até seis). Nunca reativar esses workflows pagos via commit sem revisão explícita. Mídia gerada fica na biblioteca PixelLab e, opcionalmente, nos artifacts temporários; não versionar PNG em código-fonte. Não alterar `site/office-art.js` antes de checagem visual das artes.

## Sprites animados PixelLab no escritório

A fonte de verdade é o export da biblioteca PixelLab, sem POST pago. `scripts/import_pixellab_agents.py` valida personagem, directions e os 192 frames de 88×88 antes de montar os seis atlas. Não commit-ar ZIPs originais ou JSONs contendo UUIDs, tokens, nomes pessoais, URLs e prompts; commit-ar somente PNGs de sprites e manifesto saneado. No browser, `agent-animator.js` desenha quadros já carregados, sem chamadas de API. O status visual deve refletir somente o snapshot real: qualquer demonstração de movimentos sem atividade deve ser marcada explicitamente como prévia. Falhas dos atlas preservam os avatares originais.

## Rotas e interações de ambiente

`site/agent-routines.js` contém rotas de **demonstração manual** sem agendar ações automáticas nem alterar status de agentes. Movimentos e tarefas reais sempre vêm do backend. Não fingir que ações ainda sem sprites PixelLab (cantar, beber, jogar, banheiro etc.) já estão animadas. Os marcadores WC e jogos são provisórios e devem ser substituídos por salas reais somente após geração/aprovação dos assets. Testar com `node tests/test_agent_routines.js`, validação geral e capturas responsivas.

## Produtora de vídeos em equipe grande

O gerente geral é humano. O arquivo `agentes/equipe.json` define cinco departamentos e especialistas **planejados**, que não passam a executar IA só pelo cadastro. O `videoforge/production/dispatcher.py` constrói 18 subtarefas por vídeo e só considera `done` após artefato verificável. Não transformar `ready`/planejamento em atividade real no Pages. Nenhuma mudança no fluxo autoriza publicar vídeos, rodar modelos pagos ou simular status.

O catálogo `personagens/alex/production-animations.json` lista 137 ações. As de tipo `character` são tratadas por `videoforge/pixellab/production_animations.py`; `sequence` reutiliza movimentos e `object` requer outra API. Fluxos pagos só geram movimentos ausentes, com limite por execução e autorização do gerente. Consultar `docs/EQUIPE_PRODUCAO.md` e `docs/PIXELLAB-PRODUTORA.md`.


## Recepção automática de imagens da produtora

O workflow `.github/workflows/pixellab-production-import.yml` é **somente leitura do PixelLab (GET)**: pode receber novas imagens quando os lotes existentes terminarem ou em execução manual, sem cobrar créditos. O importador aceita apenas **movimentos completamente verificáveis**, preservando imagens anteriores em caso de ZIP parcial. Não copiar ZIPs, layouts, UUIDs, URLs de prévia, prompts ou segredos para o repositório. Testar com `tests/test_pixellab_receive.py` e `tests/test_pixellab_objects_receive.py` (Pillow instalado nos jobs). Os PNGs/manifestos importados em `site/assets/pixellab/` passam por `scripts/verify_pixellab_assets.py` antes do commit e acionam Pages. Não afirmar que animações já estão conectadas ao Canvas só porque foram recebidas no Git.

## Perfis visuais de agentes corrigidos

Não usar sprites que não estejam no manifesto de produção. Perfis em `site/agent-behavior.js` escolhem movimentos de cada cargo; o modo 🎬 é demonstração opt-in para IAs não conectadas, e os passeios/conversas não atualizam o backend. As oito posições de cadeiras em `site/office-art.js` são validadas por `tests/test_office_layout.js`; ao alterar o cenário, manter espaço para os sprites de 72 px e placas sem sobreposições. Consultar `docs/CORRECOES_AGENTS.md`.

## Caminhada de agentes em pixel art

Velocidade, rotas e fase dos passos devem permanecer em `site/agent-routines.js`; FPS e viewport em `site/office-renderer.js`; desenho de frames em `site/office-art.js`. Não converter animações decorativas em estados reais de produção. Preservar `prefers-reduced-motion`, testes Node de caminhada e revisão visual desktop/mobile. Não gerar novos sprites pagos para corrigir apenas tempo/interpolação no Canvas.

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


### Distribuição dos funcionários nas salas

As oito âncoras PixelLab foram centralizadas em `site/office-map.js` (não duplicar no renderer): **Direção, Roteirista, Revisor e Publicador em Produção; Artista e Animador na Sala Criativa; Narrador e Editor no Laboratório**. Cada rótulo permanece dentro do cômodo. `site/agent-routines.js` usa o corredor inferior e a passagem superior, em vez de atravessar mesas da Produção ao sair das salas à direita. A prévia continua desacoplada do backend: ninguém é registrado como trabalhando sem evento verificável.

## Codex Proxy — integração backend segura

O proxy independente em Go tem 22 rotas, expostas pelo cliente
`videoforge/proxy/client.py`; o mapping dos 18 cargos fica em
`videoforge/proxy/roles.py`. Consulte `docs/CODEX_PROXY.md`.
**Nunca** colocar `PROXY_API_KEY`, `PROXY_ACCOUNTS_JSON`, tokens OAuth,
URLs autenticadas, respostas privadas ou estado de conta no `site/`, dados
do Pages, artefatos públicos, logs ou commits. Não copiar secretos
do AutoEditorVideo sem autorização específica; repositórios GitHub
possuem Secrets independentes.

Workflow automático/testes: somente servidor de demonstração vazio e
chave sintética. A restauração de contas privadas só é permitida mediante
`workflow_dispatch` manual em `main` e Environment `proxy-runtime`
protegido. Diagnóstico privado é read-only; não marca agentes trabalhando
nem libera IA, geração de imagens, gastos ou publicação. Toda execução
produtiva futura exige orçamento real de requisições, retry e idempotência,
aprovação do gerente, evidência de artefato, sanitização da telemetria e
separação de renderização/publicação.

## Gerentes editoriais independentes (regra de não repetição)

O novo cadastro `agentes/gerentes-canais.json` atribui exatamente um gerente
a cada um dos cinco canais. Os 18 especialistas são recursos compartilhados,
mas as tarefas, credenciais, métricas e reservas são isoladas por `channel`.
Consultar `docs/GERENTES-CANAIS.md` e os módulos
`videoforge/channel_agents/` antes de alterar pesquisa editorial.

**REGRA PRINCIPAL: jamais produzir assunto repetido.** Antes de qualquer
geração, usar inventário COMPLETO de uploads por canal + histórico
persistente de reservas; rejeitar assunto, abordagem ou título semelhantes,
inclusive material privado/agendado e tentativas anteriores. Quando o histórico
estiver incompleto ou houver títulos privados inacessíveis, interromper.
O lock local `reserve.py` NÃO garante exclusão distribuída entre runners
efêmeros: configurar persistência/locks atômicos antes da autonomia produtiva.
Somente humanos aprovam ativação de publicação. Sem OAuth autorizado, o agente
não deve afirmar métricas, tendências nem que está conectado.

O YouTube Data/Analytics é read-only em `youtube.py`: validar
`channels.list(mine=true)`, conferir ID exato, escopos OAuth e limites de
requisições; não imprimir dados privados nem expô-los ao GitHub Pages.
O `ideation.py` só utiliza Codex Proxy explicitamente autorizado, com
um chamado por execução, JSON validado e verificação posterior de duplicatas.
Não copiar Secrets do AutoEditorVideo automaticamente.

## Subgerente — avaliação baseada em QA, sem autoavaliações

O cadastro `agentes/equipe.json` inclui **exatamente um** agente adicional
(`subgerente`), o nono visual, subordinado ao gerente geral humano.
Seu posto em `site/office-map.js` é **em pé** na área colaborativa:
não renderizar outra mesa ou cadeira, nem repetir sprite sentado.
Os oito postos existentes devem permanecer com posição e pose preservadas.

`videoforge/production/subgerente.py` calcula média de pontos (0–100)
por trabalho aprovado por revisor independente. Exigir referência verificável
do artefato, trabalho único, revisor QA distinto do funcionário,
conformidade e mínimo três avaliações. Não premiar volume bruto, views,
CTR, uploads de vídeos ou fabricação de dados. A origem JSON
`trusted_backend_qa` é **uma declaração do chamador**, NÃO autenticação
criptográfica: antes da produção real implementar verificador confiável de
hash/QA no backend. Não expor hashes privados no Pages, apenas ranking agregado
e sugestões. Sem evidências, status `awaiting_verified_evidence` e sem pontos.

O Subgerente pode sugerir ações, mas **não editar arquivos, alterar outros
agentes, aumentar gastos, demitir, punir ou publicar conteúdo** sozinho.
Toda alteração de modelos/prompts/código exige aprovação humana, testes e
política de rollback. [Contrato e critérios](docs/SUBGERENTE.md).

## Regra ABSOLUTA de imagens dos vídeos: SOMENTE gerador integrado

**O assistente NAO deve gerar, desenhar ou fornecer imagens das cenas de
producao por conta propria.** As imagens de TODOS os videos de producao
devem ser solicitadas pelo executor privado a um gerador de imagens
integrado e autorizado do VideoForge AI. A escolha e a origem do provedor
devem constar na evidencia do backend; atualmente o piloto utiliza
`ProxyClient.images_generate` do Go Codex Proxy.

E PROIBIDO fazer fallback visual com Pillow/ImageDraw, formas geometricas,
placeholders, stock, imagens de conversas com ChatGPT, arte manual ou
qualquer imagem criada no codigo para substituir a falha do provedor.
Proibido tambem reciclar um quadro ou imagem de outro video como se tivesse
sido gerada para esta producao. Pode-se recortar, redimensionar, aplicar
movimento de camera e compor texto **sobre imagem realmente recebida do
gerador**, nunca inventar seu conteudo.

Se QUALQUER imagem nao for retornada ou for invalida, **interromper o job
sem renderizar um novo video**, sem upload e sem marcar a tarefa como
concluida. Erros HTTP 429 devem ser informados como indisponibilidade do
provedor, **sem retries automaticos** nem utilizacao de um provedor pago
alternativo sem autorizacao. Nunca disfarcar falha de IA com fallback local.

Regras testaveis em `config/production-image-policy.json` e verificacao
em `videoforge/production/image_policy.py`. O executor comprova a origem
a partir da resposta da API, confere arquivo e SHA-256. Um JSON de
proveniencia sem controle de execucao nao basta para comprovar a origem.
A thumbnail pode ser composta APENAS a partir de imagem ja gerada pelo
provedor (recorte e texto), e nao pode introduzir arte substituta.
Arquivos antigos de testes com imagens locais **nao** sao aceitos como
producao conforme esta regra.

## Qualidade é obrigatória antes de ampliar quantidade

A política está em \`config/quality-policy.json\` e
\`docs/QUALIDADE-E-CRESCIMENTO.md\`. Toda execução real futura deve
produzir provas de mídia com hash, revisão de QA independente e
aprovação humana. Não preencher pontuações do checklist
\`quality-review-template.json\` por simulação; não permitir que a
interface pública aprove sua própria entrega.

O planejador \`videoforge/production/dispatcher.py\` não libera a etapa
\`aprovacao\` até o portão \`quality_gate.py\` passar. Reprovar a
entrega devolve dependências para revisão; depois de no máximo duas
revisões, suspender e exigir diagnóstico. Direitos, repetição de
conteúdo, veracidade, segurança infantil e canal errado bloqueiam
imediatamente, não geram retries automáticos. Nenhum resultado de QA
libera \`publicacao\` sozinho.

Para os canais, usar \`engagedViews\` na avaliação de Shorts quando o
formato foi identificado pelo editor e comparar somente vídeos do
próprio canal na mesma janela. Dados insuficientes implicam não
concluir. Cada experimento posterior muda uma variável de cada vez;
não reutilizar pauta ou conteúdo. O piloto de 28 dias não obriga
volume, consumo de recursos nem publicação.
