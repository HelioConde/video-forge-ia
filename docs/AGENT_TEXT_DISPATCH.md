# Despacho de tarefas textuais via Codex Proxy

## Estado e escopo

O VideoForge AI tem 18 etapas de produção e 36 papéis cadastrados. O
dispatcher monta o plano determinístico, enquanto agent_dispatch identifica
apenas etapas de **texto** cujo responsável e dependências são válidos.
Os demais motores (geração de imagens, TTS, Remotion, FFmpeg, YouTube) não
são invocados pelo despachante de texto.

A escolha editorial da pauta pertence à equipe de pesquisa do canal, não
ao assistente nem a este executor. Uma demanda de produção real precisa
partir de pauta revisada e reservada. O modo de planejamento não valida
automaticamente a procedência editorial de um tema fornecido manualmente.

## Planejamento sem internet, contas ou custos

    python -m unittest discover -s tests -p 'test_agent_dispatch.py' -v

O workflow production-request.yml gera os artefatos de planejamento de
18 tarefas e o arquivo agentes-texto-prontos.json. Esse arquivo contém
somente tarefas de texto com dependências verificadas e não inclui
respostas de IA nem segredos. O modo continua planning_only, com zero
requisições ao Proxy, sem disparo automático de modelos.

## Execução de um único rascunho em backend privado

A função run_text_draft recebe um plano confiável, ID da etapa, contexto
revisado, diretório privado, autorização da execução, cliente Proxy e
modelo. Exige simultaneamente authorized=True e
VIDEOFORGE_AGENT_EXECUTION_APPROVED=yes. O runner é responsável por
aprovar custo da tarefa, modelo disponível, canal/usuário autorizado e
limites agregados por trabalho e conta.

Exemplo **ilustrativo** para uma execução somente após autorização externa:

    receipt = run_text_draft(
        approved_plan, "titulo",
        context=reviewed_script,
        private_dir=Path("output/agents-private/job-001"),
        authorized=True,
    )

O workspace exige permissões 0700. A função cria um arquivo de reserva
exclusiva 0600 antes de chamar o proxy, evitando enviar a mesma requisição
novamente num job duplicado ou quando ocorre timeout. A reserva não é
automaticamente limpa em caso de falha: é necessário reconciliar a
execução e eventuais quotas antes de tentar de novo. O resultado textual
é guardado em um arquivo de rascunho privado, também com permissões 0600,
com SHA-256 do texto e status awaiting_independent_review. O retorno
público é um recibo sem conteúdo privado.

## Salvaguardas

- A etapa precisa ser elegível em ready_tasks e ter o responsável original
  registrado na equipe. Dependências e arquivos esperados são conferidos.
- Só chat ou responses **textuais** podem ser delegados; imagens,
  vídeo, voz, publicação e aprovação humana não passam por esse executor.
- Mesmo com uma resposta do modelo, o plano original NÃO é alterado, a
  tarefa NÃO muda para done e nenhum QA é pontuado.
- Nenhum token OAuth, prompt completo, resposta ou artifact privado é
  enviado automaticamente ao Pages, ao Actions Summary ou ao Git.
- A autorização do ambiente não basta para produção em lote: o workflow
  de geração precisa futuramente de limites de custo, fonte do briefing,
  validação editorial, persistência de provas, auditabilidade e revisão
  humana antes de ativar agentes ou publicar.
- Nunca contornar HTTP 429, mudar automaticamente de provedor/modelo, ou
  repetir uma geração quando o estado de cobrança for incerto.

## Próximas fases

1. Criar tickets assinados de trabalho e um executor restrito no Environment
   protegido, com aprovações, modelo/cota validados e orçamento por vídeo.
2. Conectar revisão independente a artefatos comprovados e somente então
   atualizar estados de tarefas e ranking do Subgerente.
3. Integrar geradores de imagens e pipeline de áudio/vídeo sob suas próprias
   políticas, sem misturar as credenciais do Proxy com o Pages.
4. Conectar informações de progresso real ao escritório, com eventos de
   execução verificados e sem conteúdo confidencial.
