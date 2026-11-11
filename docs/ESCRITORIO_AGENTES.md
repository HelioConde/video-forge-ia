# Escritório virtual de agentes (GitHub Pages)

## Objetivo

Visualizar os agentes do VideoForge AI como trabalhadores em um escritório, com seus postos, estado reportado, tarefa e canal. O usuário poderá acompanhar a equipe sem misturar a interface com os processos de produção.

## Arquitetura

- **`agentes/equipe.json`**: cadastro central de oito agentes, etapas, dependências e habilitação (atualmente todos desabilitados).
- **`site/index.html`**: estrutura da página em viewport inteiro, controles sobrepostos e painel lateral.
- **`site/office-art.js`**: arte original do estúdio em Canvas 2D, com oito personagens personalizados, mesas e salas de criação/edição.
- **`site/office-renderer.js`**: motor Canvas 2D para viewport, zoom, toque, seleção, minimapa e renderização.
- **`site/styles.css`**: layout full-viewport com HUD e painel flutuantes, responsivo para mobile.
- **`site/app.js`**: coordenação de UI, zoom/fullscreen, lista de agentes/canais e leitura do snapshot.
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

## Interface Canvas 2D em tela inteira — versão 2

O espaço de trabalho ocupa toda a altura disponível da janela (100dvh, descontado apenas o cabeçalho compacto). O canvas adapta-se automaticamente ao tamanho da janela e usa renderização pixelated sem interpolação.

Recursos:
- Cenário próprio, visto de cima, com piso, divisórias, janelas, plantas, salas de reunião, mesas, monitores e oito sprites personalizados.
- Seleção de agente clicando ou tocando diretamente no cenário, com inspetor aberto ao lado (no celular: painel inferior).
- Zoom via roda do mouse ou botões +/-; arrastar para navegar, pinça com dois dedos para ampliar e botão de centralização.
- Botão para colocar o espaço de trabalho em fullscreen pelo navegador, quando suportado.
- Lista de agentes e cinco canais disponível em abas.
- Diferenciação entre sprite decorativo e trabalho real: somente eventos do backend marcam atividade. Status original `nao_conectado` permanece visível em cada agente.

Não copiar sprites, texturas ou assets do Pixel Agents. O escritório foi desenhado por código e usa apenas seus conceitos de usabilidade.

### Testes e publicações

O Actions valida JavaScript, os testes Python e a existência da estrutura de Canvas antes do deploy automático no GitHub Pages. Um deploy bem-sucedido confirma a publicação dos arquivos, **não** comprova atividade dos agentes.

## Auditoria visual em desktop e celular

A revisão por capturas locais em 1440 × 900 e 393 × 852 identificou duas falhas do primeiro layout: grande faixa vazia no celular e estação de trabalho com pouco contraste no piso.

**Correções aplicadas:** zoom inicial adaptativo no celular para preencher a altura do escritório; foco em estação ao selecioná-la na lista; minimapa clicável com indicação do viewport; tapetes individuais, placas numeradas e detalhes decorativos nas salas. A tela pode ser arrastada e ampliada; botão ⌖ retorna ao enquadramento inicial. O painel lateral não consome a área central quando está fechado.

Os screenshots de inspeção são renderizações locais do desenho em desenvolvimento. Uma publicação do Pages confirmada pelo GitHub valida deploy, não significa que os agentes executem IA.

## Pixel Studio v3 — revisão visual

A nova implementação separa a cena em `site/office-art.js` e o motor em `site/office-renderer.js`. Foi avaliada por capturas locais em 1440×900 e 393×852, incluindo seleção de funcionários no desktop e celular. O escritório agora usa tapetes compartilhados, piso com textura, ferramentas por profissão, sala de criação e estúdio audiovisual. O minimapa é recolhido por padrão em telas estreitas, preservando a visualização dos funcionários.

O Pages permanece uma visualização **estática**: a animação decorativa não implica execução de agentes, e a única fonte de atividade real são os eventos do backend. Os scripts têm validação `node --check` nos workflows e a publicação é automática quando a interface muda.


## Correção de cenário e diagnóstico de IA — novembro/2026

O cenário PixelLab foi reorganizado em 3 salas aprovadas (produção, criação e laboratório) e 3 ambientes **visuais em prévia** (copa com água, sala de jogos, WC). O catálogo isolado de objetos foi substituído por móveis contextualizados nas salas e circulação inferior, com sinalização. O layout e os destinos usam agora `site/office-map.js` como fonte de coordenadas compartilhadas, consumida por `office-art.js` e `agent-routines.js`. Os oito funcionários ganharam marcadores de profissão distintos e as sequências de interação respeitam os frames de gestos (em vez de ignorar o relógio da rotina). Nenhum sprite PixelLab pago foi regenerado.

Os oito agentes do cadastro em `agentes/equipe.json` seguem sem `modelo_ia` e com `habilitado: false`. O exportador `scripts/build_dashboard_data.py` agora adiciona diagnóstico **sem segredos** para cada papel: modelo definido, executor habilitado, dependências e existência de eventos. O painel identifica expressamente quando a IA não está ligada. O exportador valida que as dependências referenciam agentes existentes, não formam ciclos, e recusa marcar agentes sem executor/modelo como `trabalhando`, `revisao` ou `concluido` por simples relatório. **Isso melhora a integridade, mas não conecta uma API nem autoriza gastos.** Para IA real, ainda são necessários executores backend, credenciais protegidas, modelos por cargo, limites de custo e evidências de tarefas reais.

## Cena unificada gerada no PixelLab (novembro/2026)

A sede inteira é renderizada com o PNG `site/assets/pixellab/scenes/agencia-unificada.png` gerado pela API PixelLab v2. O Canvas usa nearest-neighbor; `site/office-map.js` compartilha dimensões de recorte, posições de oito postos, zonas internas, destinos (café, água, jogos, WC) e pontos de conversa; `site/agent-routines.js` usa o corredor central. Ícones e placas são overlays de Canvas para evitar depender de letras geradas na imagem. O mapa do minimapa e a seleção de funcionários seguem os mesmos pontos. Nenhuma nova execução de IA, geração paga ou upload de vídeo é disparada pela interface.
