# VideoForge AI: primeiro video de teste com execucao real

## Escopo autorizado pelo proprietario

Primeiro piloto de producao no **Otaku Multicena** (canal interno
otaku-br). Objetivo: executar uma vez o fluxo completo de previa tecnica
de **18 segundos** com historia de fantasia totalmente original, sem
imagens, musica ou personagens de franquias conhecidas.

**Nao e Short publicavel**: os Shorts seguem a regra editorial existente
de no minimo 90 segundos. Este teste curto serve apenas para provar que
as partes da empresa virtual conseguem deixar arquivos MP4 e de revisao
no GitHub Actions.

O arquivo config/pilot-first-video.json e uma requisicao unica, e sua
chegada a main dispara o workflow. Repeticoes exigem workflow_dispatch
manual. Nenhum upload no YouTube, postagem ou alteracao no AutoEditorVideo.

## Quais agentes trabalham de verdade

O arquivo videoforge/production/pilot_executor.py usa o grafo original
de 18 entregas e registra arquivos nao vazios para 15 etapas:

1. coordenador-pautas: briefing.json do projeto original
2. pesquisador: pesquisa.json, classificando roteiro como ficcao sem fatos
3. roteirista-cenas: roteiro.json; tenta o chat do Codex Proxy, fallback
   autoral explicitamente identificado caso a chamada falhe
4. titulo, descricao, tags-seo: metadados derivados do roteiro
5. storyboard: divisao em tres cenas de seis segundos
6. ilustrador: imagens PNG para tres cenas, ate tres chamadas ao Proxy,
   fallback ilustrado **local identificado** quando imagem nao esta disponivel
7. thumbnail: capa PNG produzida localmente sobre imagem da cena
8. voz: voz pt-BR via espeak-ng offline (voz robotica de teste)
9. animacao: movimento real da camera 2D (Ken Burns), nao rigging de personagem
10. legendas: arquivo SRT
11. audio: faixa WAV concatenada
12. montagem: video vertical H.264, AAC com legenda gravada no MP4
13. qa-tecnico: ffprobe e hash SHA256 calculados do MP4 real

As etapas numeradas representam as 15 entregas logicas do grafo, nao
contagem de trabalhadores humanos. As outras tres tarefas sao bloqueadas:

- revisor-conteudo: somente checklist pendente, sem fingir revisao de
  direitos, originalidade, coesao ou metricas YouTube;
- gerente geral: precisa assistir e aprovar explicitamente;
- publicacao: nao ha caminho de upload no workflow.

Subgerente, gerentes de outros canais e equipe visual do escritorio NAO
foram conectados a execucao em tempo real; o piloto registra um resultado
auditavel do departamento, sem simular trabalhadores online.

## Seguranca, custo e tempo de uso

- GitHub Environment: proxy-runtime (secrets PROXY_API_KEY,
  PROXY_ACCOUNTS_JSON).
- Cada execucao pode enviar **no maximo quatro** requisicoes generativas
  externas: um roteiro por chat e ate tres imagens.
- Cliente proxy protegido por localhost. Go compilado a partir da revisao
  fixada do projeto upstream. Nunca publica OAuth em arquivos, logs ou
  artifact do workflow.
- Tokens OAuth temporarios sao restaurados no runner com acesso restrito
  e apagados apos o teste. Renovacoes nao sao salvas de volta no secret.
- Videos, capas, roteiro e relatorios enviados para artefato do Actions
  por 7 dias. Como o repositorio e publico, trate essa previa como
  **conteudo nao privado**, embora os segredos estejam protegidos.
- O servidor utiliza interface nao oficial: chamadas podem falhar ou
  consumir cotas da conta ChatGPT; nao presumir acesso ilimitado.
- A disponibilidade dos 10 itens do catalogo nao garante acesso ao modelo
  de texto ou imagem especifico. Falhas usam fallback original local
  e o resumo do teste informa quantos resultados foram IA.
- Voz sintetica robotica e animacao por camera sao temporarios: nao
  afirmar que o video tem a qualidade final exigida para publicacao.

## Onde ver o video

GitHub > Actions > VideoForge - Primeiro video real (piloto privado) >
execucao > Artifacts > otaku-multicena-first-preview-ID.

Arquivos principais: video.mp4, thumbnail.png, manifest.json,
plano-executado.json, qa-tecnico.json e qa-conteudo.json.

O proximo passo apos visualizar e avaliar a previa sera melhorar voz,
consistencia dos personagens entre cenas, qualidade das ilustracoes,
sincronismo, narrativa e revisao de copyright, antes de qualquer
autorizacao humana de publicacao.
