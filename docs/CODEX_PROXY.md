# Integração Codex Proxy — VideoForge AI

## Objetivo e estado

Integrar o servidor **10/chatgpt-codex-proxy** ao backend, sem colocar
OAuth, `PROXY_API_KEY`, prompts privados ou respostas em `site/`/GitHub Pages.
O repositório está público e o escritório Canvas é **somente um visor público**.
A integração desta etapa contém **cliente API completo, mapeamento de tarefas
e validação**, mas **não** inicia IA por conta própria, não gera MP4, não
envia vídeos nem marca agentes como conectados.

Fonte do servidor Go: https://github.com/10/chatgpt-codex-proxy
Versão fixada, igual ao AutoEditorVideo: `1da5476e46ef62830d7016de2a931b0b8270a6c4`.
Por usar interfaces privadas de terceiros, endpoints e planos/modelos podem
mudar. Não usar para contornar quotas ou presumir uso ilimitado.

## Componentes

- `videoforge/proxy/client.py`: métodos para **22 rotas**; OpenAI Chat,
  Responses, compactação, imagens (gerar/editar, JSON com referências/máscaras),
  Anthropic Messages e contagem de tokens, streaming SSE, WebSocket
  (dependência opcional `websockets>=14`), modelos, autenticação por dispositivo,
  contas, quotas, refresh e rotação.
- `videoforge/proxy/roles.py`: associa as 18 entregas planejadas
  a capacidade do proxy, backend de render/voz ou aprovação humana.
  Não substitui `videoforge/production/dispatcher.py` e não executa tarefas.
- `videoforge/proxy/private_state.py`: restaura o JSON OAuth somente de um
  Secret **configurado manualmente pelo proprietário neste repositório**,
  com permissões 0600, diretório 0700 e exclusividade.
- `videoforge/proxy/cli.py`: catálogo offline ou preflight somente leitura.
- `.github/workflows/codex-proxy-backend.yml`: testes offline e teste real
  do servidor Go **com chave sintética e zero contas**. Um terceiro job
  (somente `workflow_dispatch` em `main`) é um preflight privado opt-in.
- `.github/workflows/production-request.yml`: gera
  `output/gerente/proxy-tarefas.json` junto ao plano das 18 tarefas,
  sem conexão ou cobrança.

## Matriz de capacidades

| Recursos | Rotas principais | Uso no VideoForge |
| --- | --- | --- |
| Texto/planejamento | `/v1/chat/completions`, `/v1/completions`, `/v1/responses` | Briefing, pesquisa, roteiro, título, descrição, tags, QA |
| Ferramentas, JSON estruturado | Mesmas rotas com `tools`, `text.format` | Agentes e contratos JSON; o executor de ferramentas é responsabilidade do backend |
| Histórico de raciocínio | `/v1/responses/compact` | Contexto longo; preservação por sessão |
| Streaming | SSE + `GET /v1/responses` (WebSocket) | Cliente privado em execução contínua; não disponível no Pages estático |
| Geração/edição de imagens | `/v1/images/generations`, `/v1/images/edits` | Imagens de cena, personagens/cenários, referências e máscaras |
| Anthropic | `/v1/messages`, `/v1/messages/count_tokens` | Compatibilidade com clientes alternativos, contagem estimada |
| Descoberta de modelos | `/v1/models`, `/v1/models/:id` | Selecionar modelos realmente retornados pelas contas |
| Health | `/health/live`, `/health` | Diagnóstico, sem gerar conteúdo |
| OAuth / contas | `/admin/accounts*` | Login manual, listagem, disable, refresh, quota, exclusão |
| Balanceamento | `/admin/rotation` | `least_used`, `round_robin`, `sticky` |

**Limites**: imagens não significam vídeos animados prontos; o editor continua
precisando de TTS, FFmpeg/Remotion, edição e YouTube em módulos distintos.
`max_tokens`, `temperature` e outros parâmetros podem ser recebidos e
ignorados pelo proxy upstream; não tratá-los como limites rígidos.
A contagem de tokens de Messages é estimada, não cobrança oficial.
Modelos e reasoning effort devem ser descobertos por conta.

## Segurança e configuração

1. **Offline sem segredos**: na pasta principal, executar:
   `python -m unittest discover -s tests -p 'test_proxy_client.py' -v`
   ou `python -m videoforge.proxy.cli --action catalog`.
2. **Servidor Go local**: use uma instância confiável do proxy fixado,
   acessível em `http://127.0.0.1:8080` ou `https://host-privado`.
   HTTP sem TLS fora do loopback é rejeitado pelo cliente.
   Não coloque chave no site; backend lê `PROXY_API_KEY` e
   opcionalmente `VIDEOFORGE_PROXY_URL`.
3. **GitHub Actions (manual, privado)**: criar em
   `HelioConde/video-forte-ia` um Environment chamado `proxy-runtime`,
   restringir deploy à `main` e, idealmente, exigir aprovação para
   uso de credenciais. Criar os Secrets **nesse Environment**:
   `PROXY_API_KEY` e `PROXY_ACCOUNTS_JSON` somente se optar por
   autorizar esse armazenamento.
4. Não copiar automaticamente o `accounts.json` nem os Secrets do
   AutoEditorVideo; credenciais exigem configuração e autorização próprias.
   Executar **Actions > VideoForge - Codex Proxy backend >
   Run workflow > mode: private-readonly** para verificar apenas o estado.
   Não publicar o JSON OAuth, logs privados ou artefatos de sessão.
5. O teste padrão `offline` usa chave artificial e nenhuma conta;
   a execução privada é **manual** e não chama geração de imagem, chat,
   login por dispositivo, upload ou outras rotas modificadoras.
6. Só habilitar geração real **depois** de implementar executor com
   autorização por trabalho, reserva atômica de orçamento, limite de
   requisições reais inclusive retries, idempotência/caching de mídia,
   auditoria de artefatos e persistência segura de refresh token.
   O proxy pode emitir múltiplas chamadas internas: orçamento de geração
   deve ser medido na aplicação, não confiando somente no campo `n`.
7. `site/data/status.json` não pode passar a `trabalhando` só porque a
   API responde; exigir evidência de tarefa efetivamente executada.

## Limitações de hospedagem

O GitHub Pages é uma página **estática**. Não é possível hospedar o processo
Go continuamente, armazenar chaves ou transmitir SSE/WebSocket privado
diretamente dali de forma segura. Existem dois caminhos futuros:

- **Sem novos serviços pagos**: workflow GitHub Actions para trabalhos
  aprovados, resultado e status públicos *saneados* por workflow;
  execução sob demanda, não chat em tempo real.
- **Controle ao vivo**: serviço backend privado (local ou hospedado com TLS)
  com autenticação própria, execução dos workers e acesso às rotas de
  streaming. O Pages recebe somente informações públicas e sem segredos.

## Critérios para a próxima fase

- Mapeamento de modelos por cargo com catálogo validado por conta.
- Motor de jobs com fila, locks, max calls, retries seguras, mensagens e
  feedback de progresso verificáveis.
- Conectores separadamente autorizados de imagem, voz, Remotion e YouTube.
- Revisor automático com QA técnico e aprovação humana antes de publicar.
- Só então ativar estados reais no escritório, com snapshot sem informações
  pessoais, credenciais, prompts e arquivos privados.
