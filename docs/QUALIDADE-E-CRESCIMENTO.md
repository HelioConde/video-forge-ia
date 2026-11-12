# VideoForge AI — Qualidade e crescimento antes de quantidade

## Regra estratégica

**O sucesso do aplicativo é crescimento sustentável dos canais por vídeos
originais melhores, não quantidade diária de MP4s.** Cada gerente pode
**cancelar, suspender ou devolver** uma entrega com problemas mesmo que isso
reduza o volume publicado. Nenhuma pontuação garante alcance ou monetização.

O piloto inicial segue \`config/pilot-otaku-multicena.json\` (28 dias). As
etapas têm **zero uploads obrigatórios**; 2–3 vídeos são hipóteses de
produção a testar, não metas que forcem material fraco. O dono da conta
mantém aprovação final de publicação.

## Fluxo real quando existir executor autorizado

1. Gerente escolhe proposta inédita usando inventário completo, reservas
   persistentes e YouTube Analytics do **próprio canal**; nada é publicado
   quando histórico está incompleto.
2. Especialistas produzem e entregam roteiro, narração, visual, título,
   descrição, tags, thumbnail, edição e revisão. Tags têm prioridade
   secundária em relação a história, voz, edição, título e thumbnail.
3. **Revisores independentes** \`revisor-conteudo\` e \`qa-tecnico\`
   avaliam qualidade com provas e justificativas. \`quality_gate.py\`
   confere a identidade de job e canal, SHA-256 do arquivo,
   stream de vídeo e áudio com ffprobe, resolução, FPS e duração.
4. O portão exige notas mínimas por critério e checklist de originalidade,
   fatos, direitos, narração, imagem, metadados, canal e revisão de
   divulgação de conteúdo sintético. Crianças têm verificações extras.
5. Decisões:
   - \`ready_for_human_approval\`: passa apenas para decisão humana;
     **não** libera automaticamente upload.
   - \`rework\`: devolve à etapa responsável e invalida os artefatos
     dependentes/QA anteriores. Até duas revisões após a primeira tentativa.
   - \`suspended\`: terceira tentativa insuficiente; para tudo até o
     gerente apresentar diagnóstico e houver reabertura humana.
   - \`blocked_policy\`: qualquer sinal crítico de repetição, direitos,
     fatos, segurança infantil ou identidade; nunca continuar por retry
     automático.
6. Após a publicação autorizada, comparar o vídeo a pelo menos três
   pares **do mesmo canal e janela**; propostas de melhoria mudam
   **apenas uma variável** por experimento. Não repetir o mesmo assunto
   só porque uma obra ou formato deu certo.

As **notas 0–100 são heurísticas editoriais internas**, NÃO métricas
do YouTube; não são geradas automaticamente nem aceitas de usuários na
página pública. O formulário de QA \`quality_template.py\` deixa todas
as notas **nulas** até o revisor preencher via backend confiável. A
avaliação de direitos é checagem de risco, não garantia jurídica.

## Arquivos implementados

- \`config/quality-policy.json\`: pesos, limites, 2 revisões e bloqueios.
- \`videoforge/production/quality_gate.py\`: verificação do arquivo MP4,
  independente de IA; devolução, suspensão e aprovação exclusivamente humana.
- \`videoforge/production/quality_template.py\`: checklist sem notas inventadas.
- \`videoforge/production/dispatcher.py\`: \`aprovacao\` só fica disponível
  após QA aprovada; rework invalida dependências. \`publicacao\` permanece
  bloqueada pelo planejador.
- \`.github/workflows/production-request.yml\`: cria
  \`quality-review-template.json\` junto ao briefing e plano dos 18 agentes.
- \`videoforge/channel_agents/youtube.py\`: além dos relatórios por
  vídeo, coleta \`engagedViews\` e \`subscribersGained\` e oferece
  \`video_retention_insights()\` para retenção por ponto no vídeo.
  A API valida identidade OAuth e vídeo antes de consultar Analytics.
- \`videoforge/channel_agents/feedback.py\`: usa \`engagedViews\` para
  Shorts **quando explicitamente identificados pelo editor**, sem inferir
  que vídeos verticais são Shorts apenas pela duração. Retorna análise
  não causal, conversão de inscritos quando possível e **um experimento**.
- \`config/pilot-otaku-multicena.json\`: planejamento de 28 dias, sem
  metas compulsórias de uploads.
- \`tests/test_quality_gate.py\` e \`tests/test_channel_managers.py\`:
  cenários sintéticos, nenhum token OAuth ou chamada de imagem.

## Métricas para crescimento

| Formato | Observar | Evitar |
|---|---|---|
| Shorts | visualizações engajadas, duração média, retenção por trecho, inscritos ganhos | equiparar starts de reprodução a engagedViews, comparar janelas de definições diferentes |
| Vídeos longos | impressões, CTR quando disponível no Studio, tempo assistido, retenção, inscritos | tratar título chamativo sem retenção como sucesso |
| Ambos | qualidade de roteiro e narração, originalidade, falhas de edição, retrabalho, tendência de crescimento por canal | atribuir causalidade a mudanças sem experimento controlado |

\`video_retention_insights()\` faz apenas GET em Analytics e exige vídeo
único e canal correto. A curva de \`audienceWatchRatio\` pode ultrapassar
1.0 por reassistidas. \`relativeRetentionPerformance\` é comparação de
retenção; não equivale a CTR. A API **não** entrega necessariamente a
taxa "ficou vs deslizou" nem o CTR das thumbnails para todo formato;
nossos relatórios não inventam esses campos.

As comparações pós-publicação utilizam janelas idênticas e formatos
editoriais identificados explicitamente. Um vídeo com dados ou pares
insuficientes **não** gera "resultado vencedor".

## Autonomia e limites atuais

O gerente de canal poderá sugerir refações. O **subgerente** ranqueia
funcionários com evidências de QA independente e melhoria verificada,
sem premiar upload em massa, para não incentivar vídeos frágeis.

Esta entrega ainda **não conecta OAuth**, não executa os agentes de IA,
não baixa métricas reais nem publica vídeo. O backend do VideoForge
ainda precisa de filas duráveis, autenticação aprovada, reservas
transacionais entre runners, provas de revisão confiáveis,
orçamento de chamadas e aprovação de publicação antes de habilitar
um ciclo produtivo automático. GitHub Pages é estático: nunca recebe
tokens, evidências privadas nem os arquivos de vídeo.

## Referências oficiais

- Guia de relatórios e métricas YouTube Analytics:
  https://developers.google.com/youtube/analytics/channel_reports
- Definições de audienceWatchRatio e relativeRetentionPerformance:
  https://developers.google.com/youtube/analytics/metrics
- Políticas de monetização e conteúdo repetitivo:
  https://support.google.com/youtube/answer/1311392

**Validação:** \`python -m unittest discover -s tests -v\`.
A aprovação de QA depende de arquivo local real + \`ffprobe\`, não dos
mocks usados nos testes.
