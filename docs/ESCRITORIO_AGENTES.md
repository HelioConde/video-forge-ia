# Escritório virtual de agentes (GitHub Pages)

## Objetivo

Visualizar os agentes do VideoForge AI como trabalhadores em um escritório, com seus postos, estado reportado, tarefa e canal. O usuário poderá acompanhar a equipe sem misturar a interface com os processos de produção.

## Arquitetura

- **`agentes/equipe.json`**: cadastro central de oito agentes, etapas, dependências e habilitação (atualmente todos desabilitados).
- **`site/index.html`**: composição da página responsiva.
- **`site/styles.css`**: cenário e personagens originais feitos com CSS.
- **`site/app.js`**: seleção de agentes/canais, indicadores e leitura do snapshot.
- **`site/data/status.json`**: dados mínimos, publicáveis. O arquivo incluído no Git é apenas um snapshot inicial com agentes não conectados.
- **`scripts/build_dashboard_data.py`**: prepara snapshot a partir de `canal/*/canal.json`, exportando somente campos não sensíveis.
- **`.github/workflows/pages.yml`**: testa e publica automaticamente mudanças relevantes da branch `main`, com opção de acionamento manual.
- **`tests/test_dashboard.py`**: valida canais, segurança básica e dados de agentes.

A página **não é o próprio orquestrador**. O backend real poderá emitir eventos de progresso verificados; os dados públicos serão regenerados e enviados ao Pages por deploy. O refresh no navegador só consulta o arquivo estático mais recente.

## Responsabilidades

| Agente | Área |
| --- | --- |
| Direção | Organização e distribuição |
| Roteirista | Temas e roteiros |
| Artista visual | Imagens, cenários e personagens |
| Animador | Camadas e movimentação |
| Narrador | Voz, áudio e música |
| Editor | Composição e FFmpeg |
| Revisor | Controle de qualidade |
| Publicador | Upload privado, agendamento e registro |

Nenhum agente acima é um processo de IA ativo até existir integração. Os cartões só representam funções planejadas.

## Referências de conceito

- [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents): visualização de agentes CLI em um escritório animado.
- [Pixel Office](https://github.com/basriayaz/pixel-office): agentes configuráveis como funcionários com cargos, memória e tarefas.

Esses projetos dependem de processos locais/servidores para os agentes. Não foram instalados no Pages nem tiveram código ou assets copiados para o VideoForge.

## Segurança e publicação

- Não colocar OAuth, chaves de API, segredos, nomes de secrets, prompts privados, IDs privados, logs de renderização ou conteúdo confidencial na página.
- A página hospedada pode estar **pública** mesmo quando o repositório está privado.
- Não simular funcionários trabalhando nem marcar tarefas como concluídas sem evento real.
- O workflow não publica vídeos nem usa modelos de IA.
- O dono precisa configurar Pages para usar **GitHub Actions**; um repositório privado pode exigir plano GitHub compatível.
- A URL do site não é considerada ativa até o GitHub reportar deploy bem-sucedido.

Veja [o guia local e a ativação do Pages](../site/README.md).

## Política permanente de publicação

- Os arquivos do escritório e seus dados públicos são publicados automaticamente pelo workflow `.github/workflows/pages.yml` em alterações relevantes na branch `main`.
- O workflow também aceita `workflow_dispatch` para republicação.
- Antes de declarar a publicação concluída, conferir o estado do Actions e a URL de Pages fornecida pelo GitHub; se houver falha, investigar.
- O site Pages pode ser publicamente acessível mesmo que o repositório seja privado. Manter a saída do exportador saneada.
- **Publicar o painel não é autorizar upload de vídeos** nem executar IAs reais.
