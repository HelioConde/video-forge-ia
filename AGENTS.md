# AGENTS.md — Regras obrigatórias de manutenção do VideoForge AI

## Meta de produto — primeiro MP4 original do Otaku Multicena pela equipe

A primeira meta executável deve ser um **vídeo 90–180s** de
`otaku-br` a partir de pauta realmente produzida pelo Pesquisador,
selecionada pelo Gerente, aprovada pela auditoria do Subgerente
e reservada após aprovação humana. A narrativa, roteiro de 90s,
camadas, imagens do gerador integrado, Edge TTS, Remotion e QA
devem possuir proveniência real. Nunca chamar uma prévia
estática de exemplo de "vídeo produzido pelos agentes".

`.github/workflows/otaku-team-video-readiness.yml` avalia
offline o registro de reservas, o manifesto e o orçamento de
imagens e emite estado **`blocked`** até as fontes privadas e
autorizações estarem realmente verificadas. Hoje o manifesto
de exemplo precisa de **26 imagens/solicitações**, enquanto o
limite padrão conservador é **12**; não aumentar gastos
automaticamente. O workflow `autoeditor-generator.yml`
não pode executar `render` por `push` ou nome de commit:
somente `workflow_dispatch` do proprietário na `main`,
`authorize_render=true` e teste offline de orçamento
**antes** do uso de segredos/proxy. O render independente por
manifesto não substitui handoff do Gerente/Subgerente.
Ver `docs/PRIMEIRO_VIDEO_OTAKU_EQUIPE.md`.

## Segurança obrigatória da pesquisa por agentes (12/11/2026)

O workflow `editorial-team-research.yml` só inicia geração mediante
`workflow_dispatch` manual do proprietário em `main`,
`authorize_research=true`, Environment protegido e `run_attempt=1`.
NUNCA reativar pesquisa paga por `push`, nome especial de commit,
arquivo de one-shot, PR ou `schedule`.

Decisões da equipe podem conter Analytics privados. Nunca subir
`output/editorial-team/decisao.json` em claro como artifact: cifrar
usando `videoforge/channel_agents/secure_report.py`,
AES-256-GCM, mesma chave do briefing e AAD do ID do run. A chave
deve estar disponível ANTES de chamar o modelo; se faltar, bloquear.
O workflow `agent-one-briefing.yml` deve validar o run de origem,
decriptar no runner e exigir reserva/aprovação humana para continuar.
Testes: `tests/test_secure_editorial_report.py`.
Nenhuma dessas melhorias autoriza gasto, ignora HTTP 429 ou
liga personagens sem trabalho comprovado.



## Regra 3 obrigatória — animação Remotion real por camada (modelo Fofinho Parte 3)

**Não renderizar apenas zoom quando o storyboard pede movimento de personagem ou objeto.** Basear a coreografia no comportamento de `AutoEditorVideo/motion-remotion/src/emanuelly-layer-stage.tsx` e no roteiro da Parte 3: gotinhas sobem e descem independentemente, Fofinho pode pular/respirar, borboletas e itens têm movimentos próprios e carinho usa mão isolada. O Storyboard especifica `motion_plan` com ID da camada, tipo, intervalo e amplitude; o **Artista** fornece o PNG com transparência, e **patinha/mão articulada exige `character_parts` extraída separadamente do corpo-base**, sem membro duplicado. O **Animador** aplica o plano no Remotion pinado usando `videoforge/motion/remotion_overlay.py` e `videoforge/motion/videoforge-motion.ts`; o **Editor** somente renderiza. O **Revisor** deve verificar contato, perspectiva, máscaras, identidade e MP4 antes de qualquer aprovação editorial. Sem parte separada, bloquear a animação da parte — não mover o corpo inteiro fingindo uma patinha. A série Kids Fofinho Parte 3 usa `canal/manu-kids/fofinho-parte03-motion-blueprint.json` apenas como referência de 18 beats, não como vídeo gerado. Em toda mudança, testar código real TypeScript do Remotion com frames e conferir as funções de cada agente no DAG. Nenhuma animação ou publicação automática sem autorização. [Manual](docs/FOFINHO_PARTE3_MOTION_REMOTION.md).

## Regra 2 obrigatória — decomposição por cena-mãe em RGBA

**Aplicar sempre que produzir imagens animáveis no VideoForge**: o Artista gera a cena completa, depois **edita essa mesma imagem** pelo Codex Proxy para obter fundo opaco sem personagens/objetos móveis, personagens transparentes e props móveis transparentes. Nunca desenhar as camadas de modo independente nem gerar mídia em chat. O Storyboard é dono do plano explícito de personagens e props; nada é extraído ou inventado sem esse plano. Exigir alfa verdadeiro, hash da cena-mãe, dimensões completas e limite previamente aprovado de chamadas. O **Revisor visual** valida o contrato técnico e encaminha para inspeção humana de identidade, encaixe, fantasmas e direitos; não confundir validação de bytes com aprovação estética. O **Animador** prepara as camadas para Remotion; o **Editor** renderiza o MP4; o **Revisor técnico** confere a saída e o Publicador fica inativo. Props separados não significam automaticamente animação articulada: o Remotion atual mantém hero_prop estático para evitar deformações de mãos. Toda alteração futura de agente ou pipeline DEVE incluir testes de limites, rotas corretas, fases, arquivos e ausência de publicação indevida. Consultar [contrato detalhado](docs/CAMADAS_CENA_MESTRE.md).

## Telemetria real dos funcionários do VideoForge

Quando o backend executa `videoforge/production/role_events.py`, o escritório deve refletir **a etapa real**: o Narrador trabalha durante Edge TTS; o Artista visual durante chamadas de imagem; o Animador durante composição; o Editor durante renderização Remotion; o Revisor durante análise técnica. Não marcar todos trabalhando só porque existe um job de vídeo. O pipeline usa context managers `role_task` e envia transições estáticas, sem prompts/segredos, ao GitHub Checks e, como alternativa independente, a GitHub Commit Statuses (`statuses:write`). A interface `site/office-live.js` valida SHA, ID do run, canal, nome da função e URL do GitHub antes de exibir atividade. O frontend nunca confunde operação do pipeline com agente de IA autônomo, nem mantém um editor trabalhando depois que o run foi encerrado. Falta de telemetria deve ser apresentada como ausência de evidência, nunca como conclusão de que ninguém trabalha.

## Regra de autoria das artes: exclusivamente o VideoForge

**O assistente de chat apenas orienta e altera contratos do VideoForge; nunca cria imagens, capas, cenas ou animações fora do pipeline para suprir o artista.** O responsável por gerar toda a mídia é o próprio VideoForge usando seu Codex Proxy, com registro de execução, custo e proveniência. Não copiar artes de chat como se fossem arquivos gerados pelo worker.

**Obrigatório para o artista em todo vídeo:**
1. Se o canal possui uma referência aprovada, usar aquela imagem como referência no primeiro desenho; caso contrário, o **próprio agente de imagem gera uma única cena 1 oficial** pelo Proxy.
2. Registrar uma bíblia visual do vídeo (personagens, rosto, cabelo, roupas, acessórios, paleta e estilo). Cada vídeo/canal escolhe seu estilo — não impor anime a conteúdo realista, kids, jogos etc.
3. Todas as cenas seguintes **devem ser chamadas de edição de imagem com a referência real da cena 1** via `ProxyClient.images_edit_files`. Nunca fazer 8 gerações independentes com apenas "consistent character" no texto.
4. Não mudar aparência, roupas, idade visual, ambiente fixo ou técnica artística entre cenas sem justificativa narrativa e revisão.
5. O revisor visual confere a sequência inteira, compara com a primeira cena e **reprova variações**. Arquivos válidos, hashes, proveniência ou API de edição NÃO provam similaridade estética.
6. Se não houver imagem de referência nem orçamento/conta para criar a âncora, interromper. Se a edição/revisão falhar, não improvisar imagem, não trocar de modelo ou gerar sem referência.
7. Nenhum MP4 pode receber aprovação editorial ou ser publicado sem evidência independente de continuidade. Um MP4 técnico de prévia pode existir com status explícito de revisão pendente, nunca marcado como qualidade aprovada.

Código responsável: `videoforge/production/visual_lock.py` e `videoforge/generators/autoeditor.py`. Testes: `tests/test_visual_lock.py`.

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

## Monitoramento gratuito e recorrente, sem execução paga

`.github/workflows/videoforge-healthcheck.yml` realiza auditorias
somente leitura com cron `12,42 * * * *` (intervalo de 30 minutos).
Confere os últimos workflows de `push` na `main` e a configuração de
9 agentes/5 canais; mantém apenas `contents: read`/`actions: read`.
Falhas detectadas produzem um run com erro, mas o monitor não cria
issues, não repete builds, não executa workflows privados nem se
autocorrige. GitHub cron é aproximado. A automação horária do ChatGPT
deve investigar as falhas reais, corrigir quando permitido e validar
novos runs. **NUNCA** inserir secrets do Proxy, YouTube ou PixelLab
neste monitor, nem permitir que cron rode geração, publicação ou
falsifique atividade. Ver `docs/MONITORAMENTO_VIDEOFORGE.md`.

## Regra operacional — sempre executar e verificar o workflow

Após modificar código, configuração, pesquisa ou documentação do VideoForge,
**não encerrar a tarefa somente com o Pull Request ou com um comando para o
proprietário executar**. O responsável pela alteração deve:

1. Acionar o `workflow run` de validação relacionado à mudança quando houver
   acesso a uma ferramenta de disparo autorizada; também inspecionar a execução
   automática de `push`/`pull_request`, se existir.
2. Acompanhar o run até o resultado definitivo e consultar jobs/logs quando
   falhar. Não afirmar sucesso sem confirmação da execução concreta.
3. Se a ferramenta conectada não permitir `workflow_dispatch`, declarar
   explicitamente a limitação, verificar os workflows automáticos disponíveis
   e indicar o comando `gh workflow run` exato como alternativa, sem fingir
   que foi disparado.
4. Não alterar os controles de segurança de uma tarefa para dispará-la
   indiretamente: nunca contornar `workflow_dispatch`, autorização humana,
   `Environment` protegido, limite de consumo, HTTP 429, credenciais,
   publicação ou revisão. Workflows que gastam cota, geram mídia ou publicam
   exigem autorização específica vigente.
5. Informar o nome do workflow, o resultado e o link do GitHub Actions. Se
   falhar, corrigir o erro verificável antes de solicitar outro teste.

Esta é uma preferência operacional explícita do proprietário para as próximas
alterações no repositório; não significa autorização permanente para produção
paga ou publicação de vídeos.

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

## Triagem de pesquisa externa sem IA

O ChatGPT pode registrar fontes e perguntas de pesquisa documentadas em
`canal/<id>/editorial/pesquisas/YYYY-MM-DD.json`. O VideoForge valida
essa entrada e, quando houver execução explicitamente autorizada,
`research_triage.py` pode cruzar **palavras-chave de série** com o
inventário completo e dados de leitura do YouTube, sem chamar o Proxy.
É uma verificação de cobertura literal, não uma seleção de pauta nem
prova de crescimento, antirrepetição temática ou agente de IA trabalhando.
Nunca exibir Analytics privados em logs/Pages, nem executar este modo
automaticamente em push/PR. O relatório da triagem privada é temporário
e não publicável. Consultar `docs/PESQUISA_EXTERNA_VIDEOFORGE.md`.

## Decisão editorial obrigatoriamente pertence à equipe

O assistente nesta conversa pode solicitar a pesquisa, fornecer
ferramentas e verificar evidências, **mas não deve escolher o tema do
vídeo no lugar dos agentes**. O time de um canal decide na seguinte
ordem: análise das métricas reais e inventário completo -> pesquisador
IA propõe várias ideias -> Subgerente bloqueia animes pausados, temas
repetidos e títulos semelhantes -> Gerente do canal ranqueia candidatas
com métricas verificáveis -> Subgerente audita a seleção e cria
evidência para revisão humana.

`videoforge/channel_agents/team.py` coordena os papéis; o pesquisador
usa `ideation.propose_candidates` exclusivamente no backend privado.
`strategy.select_idea` implementa a escolha do gerente. Nunca
codificar o anime ou tema vencedor no workflow, nem forjar trabalho
de IA: se os segredos OAuth ou o Proxy estiverem indisponíveis,
falhar e declarar bloqueio, não inventar uma decisão da equipe.

Relatório só apresenta proposta e plano; exige revisão editorial,
reserva antirrepetição antes da produção e aprovação humana para publicar.
O piloto é `otaku-br`; NÃO publicar, gerar imagens nem vídeos quando a
demanda for apenas descobrir a melhor pauta. Os registros de pesquisa
no GH Checks distinguem LLM pesquisador, decisão por métricas e auditoria.

## Gateway obrigatório dos agentes de IA

Qualquer nova inferência de modelo usada por Direção, Subgerente, gerentes e especialistas deve passar por `videoforge/proxy/client.py` e `videoforge/proxy/agent_gateway.py`, nunca por chamadas diretas concorrentes para provedores ou pelo navegador. O gateway descobre papéis em `agentes/equipe.json`, usa modelo configurado por papel e exige autorização explícita por chamada. A configuração do Proxy não habilita automaticamente funcionários, não confere cotas, não gera mídia nem publica vídeos. O runner privado deverá implementar controle agregado de orçamento, idempotência, QA e persistência de evidências antes de ligar a fila. [Documentação](docs/AGENT_PROXY_GATEWAY.md).

## Trava persistente de consumo por pauta

Antes de enviar uma chamada real ao Codex Proxy, o workflow de primeiro briefing deve registrar uma tentativa exclusiva em `canal/otaku-br/editorial/tentativas/<hash>.json`, via GitHub Contents API com **create-only** e `contents:write` limitado ao job manual autorizado. `videoforge/production/attempt_claim.py` valida o runner, a pauta preparada e a autorização, sem guardar tokens ou texto do briefing no Git. Conflito, timeout ou resultado incerto **interrompem** a tarefa e exigem reconciliação humana; nunca fazer retry automático ou apagar a tentativa para gastar cota novamente. Esta trava protege a primeira chamada de briefing, não substitui limite agregado por conta, QA ou aprovação editorial. [Manual](docs/PRIMEIRO_BRIEFING_AGENTES.md).

## Primeira chamada real de um funcionário (guardada)

`videoforge/production/editorial_handoff.py` deve validar o relatório de pesquisa dos agentes (gerente + Subgerente) e uma pauta já revisada/reservada no registro persistente do canal antes de liberar `briefing`. O workflow `.github/workflows/agent-one-briefing.yml` aceita execução privada somente por disparo manual em `main`, com duas confirmações, proprietário autenticado, Environment `proxy-runtime` e modelo já disponível. O resultado da única chamada de texto deve ser criptografado com a chave exclusiva do Environment por `videoforge/production/secure_draft.py` antes de qualquer artifact. Não salvar rascunhos, chaves ou OAuth em claro no GitHub. Não inferir pontos do Subgerente, entrega aprovada, publicação ou produção autônoma. A reserva em `reservas.json` ainda deve ter controle transacional/idempotente entre workflow runs antes de escalar o volume. [Guia](docs/PRIMEIRO_BRIEFING_AGENTES.md).

## Despacho seguro de tarefas de texto

`videoforge/production/agent_dispatch.py` conecta tarefas textuais do planejador aos especialistas cadastrados e ao `videoforge/proxy/agent_gateway.py`. A listagem e o workflow `production-request.yml` permanecem **offline**. Execuções reais requerem autorização explícita dupla, backend privado, modelo configurado e diretório privado de evidência (0700). Reservar a tarefa com criação exclusiva *antes* da chamada evita novas tentativas automáticas após timeout/cobrança incerta. O rascunho gerado tem status `awaiting_independent_review`, não deve ser contado como `done`, QA aprovado, produtividade pontuada ou progresso público sem revisão verificável. Não permitir que tarefas de texto assumam geração de imagens, TTS, renderização, upload ou aprovação humana. [Detalhes](docs/AGENT_TEXT_DISPATCH.md).

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

## Segregação OAuth da triagem de fontes externas

`.github/workflows/external-research-validation.yml`, quando usado com
`mode=youtube-readonly`, deve acessar **somente** o Environment
`youtube-analytics-readonly` e os Secrets OAuth do canal Otaku Multicena,
como em `channel-manager-analysis.yml`. Não requisitar nem transferir
Secrets de `proxy-runtime` para essa triagem. Bloquear credenciais
ausentes antes de qualquer chamada YouTube, exigir
`workflow_dispatch` protegido em `main` com `run_attempt=1`,
apagar relatório local ao sair e nunca publicar Analytics, títulos
privados ou credenciais em logs, artifact ou Pages.
Os testes de `tests/test_research_triage.py` validam também o
contrato YAML e uma execução simulada do modo privado sem rede.

## Mostrar pesquisas recebidas sem fingir trabalho dos agentes

Ao atualizar a fila `canal/<id>/editorial/pesquisas/`, o exportador
`build_dashboard_data.py` pode mostrar apenas informação pública
saneada em `canais[].pesquisa_externa`: série, alegação da fonte, pergunta,
URL HTTPS sem query/fragmentos, editor e data. O painel Canais deve
apresentar claramente "pesquisa recebida" e "pendente de checagem,
métricas e auditoria", nunca classificar como pauta aprovada.
Não associar esses registros a atividade real, pontuação, Analytics,
diretor ou Subgerente. Respeitar sanitização anti-vazamento e links
seguros. Testar exportação e UI e confirmar deploy do Pages.

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

## Diagnóstico de cotas do Codex Proxy com custo de geração zero

Para investigar HTTP 429 sem repetir pedidos de IA, usar primeiro
`videoforge.proxy.cli --action quota --usage-mode cached` em backend
protegido. Para consultar o uso atual do provider, o modo
`private-quota-live` de `codex-proxy-backend.yml` aceita apenas
`workflow_dispatch` na `main`, com Environment `proxy-runtime`,
`run_attempt=1` e um GET de uso da primeira conta elegível.
Nunca imprimir IDs de conta, e-mail, saldo, respostas do provedor,
tokens nem percentual exato; não publicar no Pages. Um GET de uso
não autoriza futuras chamadas de geração, modelo alternativo ou retries.
Ver `docs/PROXY_QUOTA_DIAGNOSTIC.md`.

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
