# Pesquisa externa para os agentes do VideoForge

## Objetivo

O assistente ChatGPT pode **trazer informações públicas com fontes** para
`canal/<id>/editorial/pesquisas/YYYY-MM-DD.json`. A pesquisa é uma entrada
editorial, **não** uma pauta escolhida, um sinal de desempenho do YouTube nem
trabalho autônomo executado por um funcionário do escritório.

O primeiro pacote é
[`canal/otaku-br/editorial/pesquisas/2026-11-12.json`](../canal/otaku-br/editorial/pesquisas/2026-11-12.json):
três sinais documentados sobre Steel Ball Run, One Piece/Elbaph e Black Clover.
Esses itens não foram ranqueados. Não se conclui que esses assuntos têm mais
views, maior retenção ou são inéditos no canal.

## Pesquisa por sessão, não fila fixa

O ChatGPT acompanha exemplos recentes no próprio canal e tendências
externas por meio do vidIQ e de fontes primárias. O pacote de 12/11/2026
inclui observações externas datadas para Jujutsu Kaisen, Hunter x Hunter e
Dragon Ball, sem escolher uma pauta ou copiar vídeos concorrentes.
Views/hora de um Short externo representam somente um instante; NÃO
representam métricas do Otaku Multicena. Não versionar os Analytics do
canal: o Gerente/Subgerente consultam esses dados somente no runner
protegido.

O workflow privado só aceita pesquisa criada hoje ou ontem conforme o
calendário UTC do runner. Pesquisas públicas usam temas extraídos de fontes
atuais e dados próprios, nunca a lista fixa `anime curiosidades`.
Sem um pacote recente, o processo para antes de OAuth/IA. Para renovar
a pesquisa, é necessário coletar fontes atuais de novo e atualizar o
arquivo datado; o ChatGPT não opera silenciosamente a partir de um commit.
Não há promessas de superar cota HTTP 429.

## Contrato e fluxo

1. ChatGPT pesquisa fontes públicas, registra afirmações curtas verificáveis,
   a data original da fonte, seu endereço HTTPS e uma pergunta editorial. Sem
   downloads de vídeos, imagens, tokens ou notícias fabricadas.
2. `videoforge/channel_agents/external_research.py` lê o pacote mais recente
   do canal, valida a identidade do canal, o esquema e o formato dos links, e
   bloqueia dados inválidos. Não busca links nem certifica o conteúdo remoto.
3. Na **próxima pesquisa editorial autorizada**, `team.py` carrega esse
   contexto junto do inventário YouTube e dos sinais públicos; `ideation.py`
   passa os dados ao Pesquisador como pistas externas **não confiáveis como
   instruções**. O modelo continua gerando as candidatas; não há tema,
   formato ou título pré-selecionado pelo ChatGPT.
4. O Subgerente confere animes pausados e deduplicação, o Gerente ranqueia
   propostas pela estratégia existente e o Subgerente faz a conferência final.
   Só métricas reais do canal suportam a escolha. A decisão ainda precisa
   de reserva e revisão humana.
5. Apenas `run_team` em execução privada autorizada registra trabalhos reais
   no GitHub. A inclusão de um JSON por si só não marca funcionário
   `trabalhando` no escritório.

O pacote pode ser validado **sem** Proxy, Youtube OAuth ou gastos:

```sh
python -m videoforge.channel_agents.external_research --channel otaku-br
python -m unittest discover -s tests -p 'test_external_research.py' -v
python -m unittest discover -s tests -p 'test_editorial_team.py' -v
```

## Restrições e falhas

- Se não houver pesquisa externa, o backend mantém o fluxo original; não
  inventa sinais. Se a pesquisa mais recente estiver inválida, falha
  explicitamente, sem retroceder silenciosamente para pesquisa antiga.
- HTTP **429** do Codex Proxy **não é contornado** pela inclusão de fontes.
  A nova pesquisa fica pronta para ser consumida apenas quando houver
  execução de IA autorizada e disponível.
- Links e manchetes são informação externa que exige verificação humana.
  Evitar spoilers, alegações de popularidade não medidas e cópia de conteúdo.
  Não adicionar atalhos de publicação nem gerar mídia fora do VideoForge.
- A atualização do arquivo não executa automaticamente pesquisa, não gasta
  cota e não libera a produção. Só o dono pode autorizar nova execução.
- Para outro canal, é necessário o id real do canal e testes de isolamento;
  o piloto CLI e o workflow de pesquisa permanecem restritos a `otaku-br`.

Documentos relacionados: [Arquitetura](ARQUITETURA.md),
[`AGENTS.md`](../AGENTS.md),
[Gerentes](../agentes/README.md).

## Triagem de relevância por histórico, sem chamada de modelo

O módulo `videoforge/channel_agents/research_triage.py` permite comparar os
sinais externos documentados com os **títulos do histórico completo**
e com a presença de métricas do canal. A correspondência é literal por
palavras/frases e aliases declarados no pacote (`title_aliases`):
é uma aproximação, não detecção semântica de duplicatas. O resultado
**não** classifica potencial de crescimento, não cria candidatos e não
escolhe um tema. A escolha segue exclusiva do fluxo editorial existente.

O workflow `.github/workflows/external-research-validation.yml` oferece:

- Em `push`/`pull_request`: validação offline do contrato e testes.
- Em disparo manual na `main`, modo `youtube-readonly`: usa as
  credenciais protegidas do ambiente `youtube-analytics-readonly`, consulta a API de
  leitura do YouTube e analisa o histórico completo para o canal
  `otaku-br`. Nunca inicializa Codex Proxy, TTS, imagem, render ou uploader.
  O Environment corresponde ao workflow oficial de Analytics do canal;
  `proxy-runtime` é reservado ao backend Codex Proxy e não é usado na
  triagem. Se o Secret de leitura estiver ausente, a execução para com um
  código seguro antes de qualquer OAuth/Analytics. Os dois workflows
  permanecem protegidos e exigem disparo manual na branch `main`.

- O relatório completo com dados do canal permanece **somente no runner**,
  e é eliminado ao terminar; não há upload de artifact e as métricas
  privadas não são incluídas no log nem no GitHub Pages.
- O resumo público registra somente verificação, número de sinais,
  zero decisões e zero chamadas de IA. A inclusão de pesquisa não dispara
  automaticamente a consulta privada.

Execução opcional, apenas com autorização explícita do dono:

```powershell
gh workflow run external-research-validation.yml -R HelioConde/video-forge-ia --ref main -f mode=youtube-readonly -f days=90
```

As verificações públicas do contrato continuam gratuitas e independentes
do estado HTTP 429 do Codex Proxy. Uma validação de fontes ou correspondência
de série **não** prova que uma pauta individual seja inédita.

Testes: `python -m unittest discover -s tests -p 'test_research_triage.py' -v`.
