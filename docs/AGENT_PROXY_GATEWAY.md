# Gateway de agentes IA via Codex Proxy

## Decisao de arquitetura

**Toda inferencia de modelo executada pelos funcionarios do VideoForge AI
deve passar pelo Codex Proxy no backend privado.** Nao criar fornecedores
alternativos diretos por funcionario. Isto inclui gerente/direcao, Subgerente,
pesquisadores, roteiristas, designers de titulos, especialistas e revisores,
quando essas funcoes precisam de IA.

O cadastro unico e agentes/equipe.json: o gateway reconhece os nove agentes
visuais e as 27 especializacoes, sem copiar IDs em outra lista.

**Importante:** ter um caminho para chamar um modelo nao significa que os
agentes estao executando. Os campos habilitado=false e modelo_ia=null
continuam corretos ate que existam executores completos, evidencia de trabalho,
auditoria e workflows protegidos. A interface nao deve exibir conexao real
por causa apenas deste gateway.

## Componentes

- videoforge/proxy/client.py: transporte e autenticacao centralizados.
- videoforge/proxy/agent_gateway.py: catalogo dos 36 papeis e uma chamada
  de texto de cada vez, com validacao, instrucao de papel e modelo configuravel.
- videoforge/proxy/roles.py: escolha da capacidade de cada uma das 18
  entregas (texto, imagem, motores externos, aprovacao).
- videoforge/channel_agents/ideation.py: agente pesquisador ja integrado
  para pesquisa editorial real autorizada.
- videoforge/production/dispatcher.py: planejamento e dependencias.
- videoforge/production/agent_dispatch.py: lista offline de especialistas
  de texto elegiveis e chamada por tarefa privada, autorizada e sem
  marcacao automatica de QA ou conclusao. Ver AGENT_TEXT_DISPATCH.md.

As rotas de texto usam ProxyClient.chat; imagens continuam com as rotas
images_generate e images_edit e com a politica de proveniencia.
TTS, sprites, Remotion, FFmpeg e YouTube nao sao substituidos pelo LLM;
a logica desses trabalhadores tambem nao deve acessar outro LLM por fora.

## Configuracao privada

- PROXY_API_KEY: segredo no backend protegido, nunca no GitHub Pages.
- VIDEOFORGE_PROXY_URL: opcional; padrao loopback 127.0.0.1:8080.
- VIDEOFORGE_AGENT_MODEL: modelo padrao, configurado pelo runner.
- VIDEOFORGE_MODEL_<ROLE_ID>: sobrescreve modelo por funcao, com hifens
  convertidos em underline (ex.: VIDEOFORGE_MODEL_SUBGERENTE).
- VIDEOFORGE_AGENT_EXECUTION_APPROVED=yes: autorizacao por execucao,
  controlada no backend, junto com authorized=True na chamada.

Antes de escolher um modelo real, consultar /v1/models atraves do cliente
protegido. Nao pressupor modelos disponiveis por conta ou uso ilimitado.

### Exemplo offline, sem gastos

    python -m unittest discover -s tests -p 'test_agent_gateway.py' -v

    python -c "from videoforge.proxy.agent_gateway import agent_proxy_catalog; print(len(agent_proxy_catalog()['roles']))"

O segundo comando deve exibir 36, sem realizar rede.

### Exemplo de invocacao em runner privado e autorizado

    from videoforge.proxy.agent_gateway import invoke_agent

    result = invoke_agent(
        role_id="titulo",
        task="Revisar tres alternativas de titulo",
        context=briefing_aprovado,
        authorized=True,
    )

O runner fornece as variaveis do Environment protegido, valida o briefing,
controla a cota, aprova a execucao e guarda a resposta privadamente. Nao
imprimir o conteudo de result em logs publicos.

## Limites e seguranca

1. O gateway nao agenda tarefas nem mantem processo de IA vivo. Uma
   invocacao faz no maximo uma requisicao Chat, sem retry automatico.
   O coordenador futuro precisa implementar reserva global de orcamento,
   idempotencia e limite por video/canal/conta antes de rodar lotes.
2. A chamada produz apenas texto e nao recebe acesso direto a arquivos,
   shell, navegador, credenciais, upload ou ferramentas.
3. Resultados devem passar por validacao de esquema, revisao independente,
   checagem factual e persistencia privada de artefatos. O retorno textual
   sozinho nao comprova que a tarefa foi feita.
4. Nenhum agente pode aprovar publicacao nem criar videos ou imagens
   automaticamente apenas por estar cadastrado no gateway.
5. GitHub Pages recebe somente estados saneados de tarefas reais com
   comprovacao. Nunca colocar keys, tokens, prompts ou respostas privadas
   no navegador.
6. Falha de autenticacao, ausencia de modelo, HTTP 429 ou resposta invalida
   bloqueia a tarefa; nao improvisar conteudo nem mudar de provedor.
7. Modelos por funcao podem ser diferentes sem criar contas separadas.
   Selecao de modelo nao e autenticacao nem permissao de orcamento.

## Proximas integracoes

- Conectar, apos validacao e autorizacao, o dispatcher ao gateway, com
  tarefas sequenciadas e resultados como artefatos.
- Criar perfis de prompt por especialista e isolamento entre canais.
- Integrar QA independente e contabilizar trabalhos no ranking do
  Subgerente, sem autodeclaracao de sucesso.
- Implantar jobs protegidos no Actions com cotas, observabilidade,
  aprovacao humana e reuso do Proxy ja configurado.
