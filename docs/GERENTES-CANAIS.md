# VideoForge — gerentes independentes por canal

## O que muda

Cada um dos **cinco canais** possui seu gerente de estratégia editorial,
identidade YouTube, regras e histórico de reservas separados:
`agentes/gerentes-canais.json`. Não usar um gerente global que misture
métricas ou conteúdos de canais diferentes.

O proprietário continua sendo o gerente geral humano e o motor de 18 tarefas
`videoforge/production/dispatcher.py` fornece especialistas reutilizáveis.
Os especialistas podem atender mais de um canal, mas cada trabalho carrega
`channel_scope` e nunca utiliza dados, histórico ou credenciais de outro canal.

### Exemplo — Otaku Multicena

1. O gerente `gerente-canal-otaku-br` verifica por OAuth que controla
   `UCXGYTuBYn-0Ziqin5ajKhOw` antes de qualquer consulta.
2. Data API v3 obtém **todos os uploads acessíveis** pela playlist de uploads
   (incluindo privacidade quando disponível), título, duração e IDs reais.
   Analytics v2 coleta por vídeo `views`, `estimatedMinutesWatched`,
   `averageViewDuration`, `averageViewPercentage` e `likes`
   numa janela igual (28/90/180 dias).
3. O gerente pontua **duração, animes e gêneros com amostras suficientes**;
   em ausência de evidência, retorna `insufficient_metrics` — não inventa
   que um assunto é o "melhor". O formato short-like é aproximado por duração
   e NÃO significa confirmação oficial de Short (falta proporção de tela).
4. Pesquisa externa opcional via Data API `search.list` (no máximo duas
   buscas por análise), apenas para gerar hipóteses. Dados públicos de
   concorrentes **não** trazem sua retenção ou Analytics interno.
5. O agente de ideação `videoforge/channel_agents/ideation.py` pode pedir
   **uma** proposta em JSON ao Codex Proxy, somente após autorização explícita,
   modelo selecionado e histórico verdadeiro. Não reutiliza vídeo de outro
   criador e não inventa notícias/fatos.
6. **Regra principal:** antes da escolha e novamente **dentro do lock de
   reserva**, rejeitar tópicos repetidos por identidade, similaridade,
   histórico de títulos publicados/privados e registros em andamento.
   Se dados estiverem incompletos, bloquear em vez de presumir novidade.
7. Uma ideia escolhida produz `videoforge/channel-manager-plan/v1`
   com as **18 entregas** do dispatcher, incluindo roteiro, narração,
   título, descrição, tags, storyboard, visuais, edição, QA e publicação.
   Título/descrição/tags dependem do roteiro; a narração usa duração/ritmo
   recomendados; publicar depende de QA e de aprovação específica.
8. O agente acompanha performance posterior e muda hipóteses de formato,
   duração e gênero com base em janelas comparáveis, não por impressão.
   Ainda **não** existe agendamento ou executor ativo para esse ciclo.

### Política de duplicação

`canal/<id>/editorial/reservas.json` é um registro **inicial vazio**,
separado por canal. **Vazio não significa que o canal nunca publicou.**
É obrigatório primeiro coletar o inventário YouTube completo, inclusive
vídeos privados acessíveis, e validar ideias por semelhança textual.

`videoforge/channel_agents/reserve.py` implementa reserva atômica local
com lock exclusivo + revalidação e gravação via rename. Para usá-la
**entre máquinas/workflows concorrentes**, o arquivo precisa estar em
armazenamento PERSISTENTE protegido, com bloqueio distribuído/CAS ou banco.
**GitHub Actions tem discos efêmeros:** artifact temporário ou commit não
coordenado não substitui um serviço de reservas confiável. Até existir
persistência transacional, o planejamento fica bloqueado para produção
automática. Similaridade é heurística: revisão de contexto/fatos continua
necessária para não repetir assunto com título diferente.

Vídeos removidos ou com título "Private video" sem metadados impedem
liberação da pauta até serem revisados. O canal Otaku Multicena mantém a
pausa editorial de *Death Note* já decidida anteriormente.

### Regras de autoaprendizado

- Comparar vídeos do mesmo canal, mesma janela e com amostra suficiente;
  medir retenção, tempo assistido, views e, quando disponível, engajamento.
- Registrar formato/gênero/anime/tema no ato da reserva para futura
  classificação baseada em dados (o YouTube não entrega esses campos
  editoriais como classificações oficiais).
- Reavaliar ideias depois da publicação usando medições comparáveis,
  controlar fadiga de temas e alternar experimentos editoriais.
- Não fazer clickbait enganoso, não fabricar fontes e não copiar cenas
  ou conteúdo protegido para criar produção meramente repetitiva.
- A principal regra é **não repetir conteúdo**, mas números e algoritmos
  não garantem aumento contínuo de audiência.

## Arquitetura

- `videoforge/channel_agents/youtube.py` — cliente YouTube Data/Analytics
  SOMENTE GET, refresh OAuth em memória, verificação de identidade,
  paginação até 5.000 uploads, limite de 180 requisições, tendências opcionais.
- `strategy.py` — análise de desempenho por amostra e classificação
  cautelosa de tempo de vídeo, anime e gênero (derivados de títulos).
- `feedback.py` — comparação pós-publicação com pelo menos três pares da mesma janela; sugere experimentos, sem alegar causalidade.
- `dedup.py` — bloqueio de repetições e quase-duplicatas.
- `reserve.py` — reserva local/atômica somente no backend persistente.
- `ideation.py` — uma chamada ao Codex Proxy autorizada, saída JSON validada,
  sem side effects, seguida por checagem editorial determinística.
- `manager.py` — instância de gerente por canal e distribuição dos trabalhos.
- `agentes/gerentes-canais.json` — cadastro independente de cinco gerentes.
- `canal/<id>/editorial/candidatos.json` — hipóteses sem métricas inventadas
  (vazias até pesquisa ou integração real).
- `.github/workflows/channel-manager-analysis.yml` — CI offline, e
  preflight manual read-only (quando segredos estiverem configurados).
- `scripts/build_dashboard_data.py` — exportação saneada para
  `site/data/status.json`. Nenhum ID OAuth, refresh token, ranking privado
  ou estado "trabalhando" aparece só por cadastro.

## Preparação do OAuth

Criar Environment **`youtube-analytics-readonly`** no repositório
`HelioConde/video-forte-ia`, com aprovação e restrição à `main`.
Configurar por ação explícita do proprietário:
- `YOUTUBE_CLIENT_JSON` do cliente OAuth.
- Uma credencial **isolada por canal**: `YOUTUBE_OTAKU_BR_TOKEN_JSON`,
  `YOUTUBE_OTAKU_EN_TOKEN_JSON`, `YOUTUBE_GAMER_TOKEN_JSON`,
  `YOUTUBE_MANU_KIDS_TOKEN_JSON` ou `YOUTUBE_ALCHEMY_LAB_TOKEN_JSON`.
- Os registros OAuth precisam incluir os escopos
  `youtube.readonly` e `yt-analytics.readonly`. Não usar credencial de
  upload na coleta e não copiar Secrets do AutoEditorVideo sem autorização.

O workflow manual `youtube-readonly` renova o token só em memória,
confere identidade, obtém dados e apaga o relatório temporário ao finalizar.
**Nunca sobe o histórico privado de Analytics para artifacts públicos.**
Modo offline pode ser executado a qualquer momento sem Secrets.

Fontes: https://developers.google.com/youtube/analytics/reference/reports/query
e https://developers.google.com/youtube/data/reference/rest

## Status honesto

**Implementados:** contratos, gerentes, coleta GET autenticada, análise
determinística, controle antirrepetição, proposta via proxy com guarda de
autorização, planejamento de 18 especialistas, reserva local transacional,
testes offline, interface com gerentes identificados.

**Não implementados/ativados:** OAuth do novo repositório, coleta real
nesta sessão, armazenamento privado transacional multi-run, ideação em
produção, workers gerando mídia, TTS/edição real, publicação ou
agendamento autônomo. O avaliador de desempenho pós-publicação já
possui código e testes, mas o loop recorrente automatizado depende de
conexão autorizada e armazenamento persistente privado. O painel deve continuar marcando os gerentes como
`nao_conectado` até evidência real de execução.
