# Primeiro briefing real pelo Codex Proxy (somente com aprovação)

## Resultado desta etapa

O workflow manual **VideoForge - Briefing IA protegido (um agente)**
em .github/workflows/agent-one-briefing.yml conecta uma decisão editorial
do time Otaku Multicena ao especialista coordenador-pautas pelo gateway
Codex Proxy. A infraestrutura funciona por jobs efêmeros; o Pages continua
apenas exibindo o escritório e NÃO carrega chaves nem executa agentes.

A execução padrão **offline** é um teste sem OAuth ou chamadas de modelo.
O modo **one-approved-briefing** existe para um único rascunho textual
após revisão humana e configuração de segredos. Não faz roteiro completo,
imagem, áudio, MP4, upload ou pontuação do Subgerente.

## Pré-requisitos para a primeira chamada real

1. Ter um relatório real, bem-sucedido, da action
   .github/workflows/editorial-team-research.yml na branch main do mesmo
   repositório, produzido pela equipe com métricas do canal e análise do
   Subgerente. Anotar o ID numérico da execução; o workflow baixa apenas
   o artifact otaku-multicena-agents-decisao-<run_id>.
2. Revisar a pauta selecionada e checar novamente o histórico do canal
   para impedir repetição. O assistente NÃO escolhe o tema no lugar da
   equipe. Persistir no registro
   canal/otaku-br/editorial/reservas.json uma reserva aprovada por humano.
   Exemplo do formato de um item em entries (valores ilustrativos apenas,
   NÃO copiar como reserva real):

       {
         "id": "<id-exato-da-pauta-escolhida>",
         "source_run_id": "<id-do-workflow-real>",
         "titulo_provisorio": "<titulo-exato-do-relatorio>",
         "status": "approved_reserved",
         "human_approved": true,
         "topic_key": "<fingerprint-verificado-da-pauta>"
       }

   Uma pauta sugerida NÃO é reserva nem licença para gerar conteúdo.
   O registro real deve ser persistido após avaliação de originalidade,
   de direitos e de eventos de publicação anteriores. O runner exige o ID,
   título, fonte e status idênticos aos do relatório.
3. O GitHub Environment proxy-runtime deve existir no repositório, restrito
   à branch main e preferencialmente com reviewers/aprovação. Deve conter
   PROXY_API_KEY e PROXY_ACCOUNTS_JSON, já preparados de modo privado,
   e um novo secret VIDEOFORGE_DRAFT_ENCRYPTION_KEY_B64, com 32 bytes
   aleatórios codificados em base64. Gere localmente com Python:

       python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"

   Guardar a chave em segurança: sem ela o rascunho enviado como artifact
   criptografado não poderá ser recuperado. Nunca colar a chave em issue,
   PR, screenshot ou logs.
4. Em Actions, selecionar **VideoForge - Briefing IA protegido (um agente)**,
   branch main, modo **one-approved-briefing**, ID da execução de pesquisa,
   um modelo textual realmente listado em /v1/models, e marcar as duas
   confirmações de uma chamada e da reserva humana. Sem essas condições,
   o job privado NÃO executa. O usuário que dispara deve ser HelioConde.
5. O runner valida a origem do workflow e a reserva ANTES de carregar
   credenciais. Compila o proxy upstream fixado, verifica a lista de
   modelos reais, faz no máximo uma chamada Chat ao coordenador de pautas
   e salva o rascunho como artifact AES-256-GCM. Duração da sessão é
   limitada, sem retries automáticos nem bypass de HTTP 429.
6. Depois da execução, baixar o artifact criptografado e revisar o texto
   **offline** num ambiente confiável com a mesma chave. Uma API local
   de leitura existe em videoforge/production/secure_draft.py:
   decrypt_private_draft(envelope_path, key_b64=secret). Não imprimir
   respostas ou chaves no GitHub Actions.

## Auditoria e limites

- O relatório deve ter sido produzido pela Action editorial legítima
  (repo, main, workflow, event, conclusão e artifact confirmados).
- O código confere o Subgerente e o gerente do canal, bloqueia Death Note
  enquanto pausado e exige reserva humana persistida.
- Nenhuma execução privada roda ao abrir PR, receber push, agendar workflow
  ou iniciar modo offline. A execução real exige a branch main, o dono da
  conta, tentativa inicial, duas autorizações e o Environment protegido.
- O ticket por tarefa é exclusivo dentro da execução efêmera; execução
  repetida em outro workflow ainda depende de nova autorização humana.
  **Não há trava persistente de consumo de pauta entre execuções**; esta
  precisa ser adicionada antes de produção autônoma recorrente.
- O artifact público contém apenas nonce e ciphertext autenticado;
  credenciais, respostas e tokens nunca são enviados em claro.
- O rascunho é awaiting_independent_review; não aprova o QA, não pontua
  funcionários e não libera publicação. A revisão e o aceite do conteúdo
  precisam de um fluxo separado.
- Se faltar Source Report, reserva, aprovação, modelo ou chave AES, o job
  falha antes de fazer uma requisição generativa.

## Testes

    python -m unittest discover -s tests -p 'test_editorial_handoff.py' -v
    python -m unittest discover -s tests -p 'test_secure_draft.py' -v

O segundo teste usa a dependência opcional cryptography. O workflow
instala a biblioteca para validar a cifra em Linux. Nenhum teste utiliza
OAuth ou realiza chamadas a serviços pagos.

## Próximo passo

Persistir uma reserva/lock idempotente de uso único entre runs com
controle de custo e auditoria, conectar uma revisão independente real,
e somente então liberar execução sequencial de roteirista, título,
descrição e outros especialistas. A publicação permanece bloqueada.
