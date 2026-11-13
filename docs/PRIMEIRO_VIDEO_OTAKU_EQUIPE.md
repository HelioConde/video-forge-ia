# Primeiro vídeo do Otaku Multicena produzido pela equipe

## Resultado desejado

Um **Short original de pelo menos 90 segundos**, com tema escolhido pelo
Gerente Otaku Multicena a partir do inventário real do YouTube e de
hipóteses produzidas pelo Pesquisador, auditadas pelo Subgerente,
depois roteirizado, ilustrado por gerador integrado ao VideoForge,
narrado por Edge TTS, animado/renderizado no Remotion e revisado
tecnicamente. O resultado inicial é **MP4 privado para revisão**,
não uma publicação YouTube nem qualidade editorial aprovada.

Uma prévia de fantasia de 18 segundos, testes sintéticos, personagens
animados do escritório ou o manifesto de exemplo **não substituem**
esse objetivo.

## Onde o fluxo está realmente bloqueado

A situação em 12/11/2026, conforme a `main`:

1. **Pesquisa autorizada:** nenhuma conclusão real recente do
   `editorial-team-research.yml` com candidatas aprovadas após o
   HTTP 429; as pesquisas externas do ChatGPT são só sinais.
2. **Reserva editorial:** `canal/otaku-br/editorial/reservas.json`
   está sem entradas. Não inventar tema, aprovação ou seleção.
3. **Briefing do especialista:** requer relatório cifrado de run real,
   reserva e aprovação humana, depois uma chamada textual separada;
   não foi convertido em roteiro completo de 90–180s.
4. **Manifesto e orçamento:** o arquivo
   `geradores/autoeditor/exemplo-manifesto.json` é uma narrativa
   original sobre uma torre, **não** a pauta escolhida por agentes.
   Tem 8 cenas, requer **26 solicitações de imagem** (cenas-mãe,
   personagens e camadas), contra o limite padrão conservador de **12**.
   Esse arquivo não deve ser publicado como vídeo do canal.
5. **Cota e geração:** o Codex Proxy reconheceu uma conta/modelos, mas
   chamadas de texto retornaram HTTP 429. Status de quota real e
   capacidade específica de imagens continuam por confirmar.
6. **Revisão final:** direitos, originalidade, continuidade visual,
   áudio, sincronia e retenção exigem checagem independente e, para
   qualquer publicação, aprovação explícita do responsável.

## Novo workflow sem custos

`.github/workflows/otaku-team-video-readiness.yml` executa
testes e, na `main`, gera um **Job Summary** sobre:

- existência de reserva editorial (sem presumir que foi autenticada);
- validade estrutural e natureza de exemplo/produção do manifesto;
- número de chamadas de imagens previstas, limite e diferença;
- itens que ainda exigem origem privada validada, decisão do Gerente,
  auditoria do Subgerente, quota e autorização humana.

`can_render_now: false` é proposital: este verificador offline
**não pode** ler o relatório AES-GCM nem as credenciais privadas e não
deve liberar produção confiando apenas em JSON. A saída com estado
`blocked` é um **diagnóstico correto**, não falha dos testes.

Execução manual de leitura, sem Codex Proxy nem MP4:

```powershell
gh workflow run otaku-team-video-readiness.yml -R HelioConde/video-forge-ia --ref main
```

Um manifesto de produção distinto deverá existir, com roteiro original
escrito/revisado pelos especialistas. Ele terá de ser associado a uma
decisão editorial real e autenticada **no runner protegido** antes
que o sistema possa considerá-lo produção dos agentes.

## Segurança do renderizador existente

Em `autoeditor-generator.yml`, o modo `render` agora exige
`workflow_dispatch` explícito do proprietário na `main`,
`authorize_render=true`, `run_attempt=1` e o
Environment protegido `proxy-runtime`. Não há mais render pago
por texto de commit ou `push`.

Antes de compilar o Proxy ou carregar os Secrets, o job valida o
manifesto e exige que o limite **expressamente informado** cubra as
imagens previstas pelo plano. O limite padrão fica em **12 para
segurança**, e o exemplo precisaria de no mínimo 26 — **não há
aumento automático do orçamento**.

O render existente continua sendo um gerador de **prévia por manifesto**;
ainda não significa que o Pesquisador, Gerente e Subgerente
aprovaram aquele conteúdo. Nunca classificar uma prévia assim
como "vídeo feito autonomamente pela equipe".

## Ordem para entregar o primeiro MP4 da equipe

1. Realizar o diagnóstico privado de quota, sem gerar conteúdo.
2. Garantir que a conta e os modelos necessários estejam de fato
   disponíveis, sem contornar o 429 nem repetir tentativa de resultado
   incerto.
3. Rodar pesquisa real autorizada do Otaku Multicena, com Analytics,
   gerar candidatas e obter seleção **auditada**.
4. Revisar e registrar aprovação/reserva persistente da pauta.
5. Gerar e aprovar briefing, roteiro, cenas, prompts e plano de camadas
   de **90–180 segundos** com rastreabilidade ao run real da equipe.
6. Fazer pré-validação do manifesto e autorizar explicitamente o
   limite de solicitações previsto para imagens.
7. Gerar artes pelo Proxy integrado, TTS, animação e MP4 real; o
   workflow interrompe caso faltem imagens — sem placeholders.
8. Inspecionar MP4, hash, legendas, som, movimento, originalidade,
   direitos e qualidade da capa. O primeiro resultado é para revisão,
   sem upload automático.

O objetivo é **um MP4 original e verificável** antes de escalar
para os cinco canais. A disponibilidade de um workflow ou uma
simulação bem-sucedida não significa que um vídeo já foi gerado.

[Testes de prontidão](../tests/test_otaku_video_readiness.py) ·
[Motor de produção](../videoforge/generators/autoeditor.py) ·
[Handoff protegido](PRIMEIRO_BRIEFING_AGENTES.md) ·
[Cota do Proxy](PROXY_QUOTA_DIAGNOSTIC.md).

## Planejamento offline do manifesto provisório (13/11/2026)

Em `.github/workflows/autoeditor-generator.yml`, um `push` na própria
orquestração ou em `canal/otaku-br/videos/**/manifest.json` executa
somente o job `plan`. Na ausência de input manual, esse teste usa
`canal/otaku-br/videos/spy-family-2027-preview-rascunho/manifest.json`
para produzir um artefato de planejamento sem credenciais, sem geração
remota de imagem, sem MP4 e sem publicação. A exceção legada baseada
em mensagem de commit foi removida: nenhuma mensagem pode inibir os
testes de planejamento ou ativar `render`.

O verificador `.github/workflows/otaku-team-video-readiness.yml` também usa agora o manifesto provisório do Otaku como padrão e o reavalia a cada alteração nele; seu resultado segue `blocked` até que as exigências de pesquisa, reserva e autorização sejam comprovadas.

O modo de diagnóstico `private-quota-live` do workflow do Proxy
**não** faz parte desse fluxo offline. O trabalho de produção real
continua separado, exige `workflow_dispatch` e salvaguardas de
aprovação e orçamento, além das condições editoriais acima; a prévia
provisória não constitui decisão validada dos agentes.

O verificador de prontidão agora identifica manifestos com ID terminado em
`-rascunho` como `provisional_draft` e informa explicitamente o bloqueio
`PROVISIONAL_DRAFT_NOT_SELECTED_BY_TEAM`. Esse marcador não substitui a
validação privada do Gerente/Subgerente e não autoriza geração de imagens,
renderização ou publicação; os demais manifestos também continuam exigindo
proveniência autenticada.

### Primeiro Otaku: manifesto explicitamente selecionado e teto de 30 imagens (13/11/2026)

A autorização atual cobre no máximo **30 solicitações de imagem** para
`otaku-br` neste primeiro MP4 de revisão. O preflight protegido do workflow
`autoeditor-generator.yml` e o executor Python bloqueiam `max_image_calls > 30`
para esse canal **antes de qualquer chamada ao Proxy ou TTS**; demais canais
conservam seus próprios limites. O formulário de `workflow_dispatch` não
sugere mais automaticamente o manifesto genérico
`geradores/autoeditor/exemplo-manifesto.json`: o proprietário deve informar
explicitamente o caminho do manifesto aprovado. O planejamento automático por
`push` continua somente offline e pode usar o rascunho como exemplo.

Essa proteção **não** comprova decisão dos agentes nem cota disponível, não
executa geração por `push`, não contorna o Environment `proxy-runtime` e
não autoriza publicação no YouTube.
