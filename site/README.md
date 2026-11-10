# VideoForge AI — Escritório de Agentes

Site estático original em `site/`, com **Canvas 2D em tela inteira**, inspirado no conceito de escritórios pixel-art de agentes, como Pixel Agents para VS Code. O código e os gráficos são próprios, sem copiar ativos visuais de terceiros.

## Executar localmente

```bash
python scripts/build_dashboard_data.py
python -m http.server 8000 --directory site
```

Abra `http://localhost:8000` para visualizar o escritório fullscreen com os oito agentes e os cinco canais. Use mouse/toque para selecionar os personagens, arraste para navegar, use scroll/+/− para zoom e o botão ⛶ para fullscreen.

## Publicação automática do GitHub Pages

1. Em **Settings → Pages → Build and deployment**, configure **Source: GitHub Actions**.
2. Verifique se sua conta GitHub permite publicar Pages de um repositório privado.
3. Revise a visibilidade da página e os dados que ficarão públicos.
4. O workflow **VideoForge AI - Escritorio de Agentes (Pages)** inicia automaticamente a cada alteração relevante na branch `main` (interface, agentes, canais, exportador ou testes).
5. Para republicar sem mudanças, use **Actions → VideoForge AI - Escritorio de Agentes (Pages) → Run workflow**.
6. Após o primeiro deploy bem-sucedido, consulte a URL indicada em **Settings → Pages**.

A publicação é automática em commits relevantes para o painel e também pode ser iniciada manualmente. **O usuário já escolheu GitHub Actions como fonte do Pages.** Como sites Pages podem ser públicos, mantenha somente nomes de canais e funções públicas no snapshot.

## Limitações atuais

GitHub Pages é estático: **não hospeda agentes reais**, não inicia tarefas, não envia vídeos, não instala bibliotecas de orquestração e não conhece automaticamente o que os agentes executam. Cada funcionário aparecerá como **não conectado** até uma execução de backend confiável fornecer seus eventos.

O script `scripts/build_dashboard_data.py` monta dados com os **nomes e modelos** dos canais e sem IDs do YouTube, tokens, segredos ou logs privados. A página tenta atualizar o snapshot a cada minuto, mas isso não é acompanhamento em tempo real: precisa existir um novo deploy para aparecerem novos estados.

## Integração futura do backend

O gerador suporta opcionalmente `--events caminho/relatorio.json` com um JSON controlado, por exemplo:

```json
{
  "agents": [
    {"id": "roteirista", "status": "trabalhando", "canal": "otaku-br", "tarefa": "Planejando um vídeo"}
  ]
}
```

IDs: `diretor`, `roteirista`, `artista`, `animador`, `narrador`, `editor`, `revisor`, `publicador`. Estados aceitos: `nao_conectado`, `aguardando`, `trabalhando`, `revisao`, `concluido`, `erro`.

Esse relatório precisa ser criado por jobs reais e revisado para evitar vazamento de informações, não por simulação de atividade. A execução manual atual **não** incorpora nenhum arquivo de eventos.

**Segurança:** o site GitHub Pages pode ficar público mesmo com código em repositório privado. Nomes públicos dos canais e as funções da equipe podem ser vistos por visitantes. A publicação automática assume que a exposição de nomes públicos de canais e funções da equipe foi autorizada; nunca adicionar dados privados ao exportador.

## Estrutura do frontend

- `index.html`: barra compacta e Canvas ocupando todo o espaço restante, com controles sobrepostos.
- `styles.css`: adapta o HUD, botões e painel flutuante a desktop e celular.
- `office-art.js`: arte Canvas 2D original — cenário, iluminação, mobiliário, objetos de cada profissão e oito personagens diferentes.
- `office-renderer.js`: motor de viewport, zoom/arraste, minimapa, hit-testing e desenho da arte no Canvas.
- `app.js`: busca o snapshot público, atualiza indicadores, gerencia seleção e inspector.
- `data/status.json`: estado mínimo exportado do backend.

Toda a arte é programática e própria. Não importa bibliotecas nem assets do Pixel Agents. Animações de interface não significam execução de trabalho.

## Navegação aperfeiçoada

- **No celular:** o zoom padrão prioriza preencher a altura da janela, eliminando grandes faixas vazias; arraste para visitar outras mesas.
- **Minimapa clicável:** localize uma estação e mova a câmera tocando no mapa no canto inferior direito.
- **Seleção pela lista:** ao tocar em um funcionário, a câmera foca o respectivo posto no celular.
- **Centralização:** use o botão ⌖ para voltar ao enquadramento original.
- **Arte aprimorada:** tapetes, placas de postos, avisos de planejamento e console gráfico de edição são desenhados no próprio Canvas.

## Pixel Studio v3

A versão atual reorganiza o cenário em três ambientes, com piso texturizado, móveis desenhados em Canvas, janelas, plantas, iluminação de teto, salas de criação e edição e personagens com roupas e ferramentas próprias.

O minimapa fica **recolhido no celular** para não encobrir os trabalhadores. Toque em "Minimapa" para expandi-lo. O status dos agentes continua baseado exclusivamente no snapshot gerado pelo backend, sem simulação de tarefas executadas.

A arquitetura visual separa **arte** (`office-art.js`) de **interação** (`office-renderer.js`). Qualquer nova personalização deve respeitar essa divisão e a regra permanente de organização do repositório.

## Cenários PixelLab incorporados ao Canvas

As imagens **originais aprovadas** estão versionadas em `site/assets/pixellab/`: três salas 256×256 px e seis objetos transparentes 64×64 ou 96×96 px. O arquivo `manifest.json` registra dimensões e SHA-256 de cada imagem. Foi produzido a partir dos artifacts das execuções PixelLab 42844340885 e 42845029772.

O botão **▦ / ✦** na barra de ferramentas alterna entre a arte original e a composição PixelLab. O modo PixelLab é habilitado automaticamente após carregar os nove PNGs; se qualquer arquivo falhar, o escritório antigo continua funcionando. O Canvas desenha as três salas sem distorção, posiciona os seis objetos sem fundo e mantém oito agentes selecionáveis. O minimapa e o foco de agentes usam os mesmos slots da arte ativa.

Os agentes ainda são desenhados pela arte original de `office-art.js` (sem spritesheet de personagem ligado); o estágio atual conecta **cenários e objetos**, não as 48 animações de personagens. O código não chama a API PixelLab no navegador, não transmite tokens e não altera o status real dos agentes. A interface do escritório continua sendo uma projeção de dados do backend.

## Sprites animados Alex — integração v4

O PixelLab exportou `character-frames.zip` com seis movimentos (`idle`, `walk`, `type`, `sit`, `talk`, `wave`) e oito direções. Cada combinação possui quatro frames de **88×88** pixels (área útil 64×64 com margem transparente). A action `pixellab-import-alex.yml` valida a identidade da exportação e monta os seis atlas PNG em `assets/pixellab/agents/alex/`. Cada atlas tem **352×704**: quatro colunas de frames e oito linhas de direções. O manifesto controla ordem, dimensões e hashes sem IDs privados.

O novo `agent-animator.js` carrega os seis atlas em paralelo, valida dimensões e oferece desenho síncrono, sem `await` dentro do Canvas. `office-art.js` escolhe a animação conforme o status **real** do agente; sem eventos de backend o agente fica em `idle`. O botão de prévia no painel de agentes percorre os seis movimentos sem alterar o status registrado. Para conforto, `prefers-reduced-motion` usa o primeiro frame.

Se faltar algum atlas, a aplicação mantém os oito personagens desenhados originalmente e o restante do escritório continua funcionando. **Por enquanto os oito postos reutilizam a aparência Alex**; personagens distintos podem ser cadastrados depois. O navegador não chama a API PixelLab nem usa credenciais.

## Testes automáticos do atlas

Os testes `tests/test_pixellab_atlases.py` validam que os seis atlas e o manifesto estão no repositório, que cada PNG tem dimensão **352×704**, RGBA e hash SHA-256 correspondente, e que a lista de direções e frames é estável. A validação e o deploy de Pages verificam a sintaxe de `agent-animator.js` com `node --check`.


## Rotinas visuais de descanso (protótipo)

O novo módulo `site/agent-routines.js` permite escolher manualmente um agente no **modo PixelLab** e mostrar sua caminhada até pontos sinalizados de café, água, jogos e entrada do banheiro. O painel possui os comandos de ida e **Voltar à mesa**. A movimentação usa `walk` com oito direções e `idle` ao chegar. O caminho usa um corredor visual predefinido, não é pathfinding completo por colisão. O minimapa e hit-testing seguem a posição do sprite durante o deslocamento.

**Muito importante:** trata-se de demonstração gráfica acionada pelo usuário, sem alteração do `status` recebido no backend, sem simular trabalho, sem rotina autônoma real. Não existe ainda animação para beber, jogar, cantar sentado, levantar da cadeira, entrar no banheiro ou lavar as mãos: ao chegar, o sprite fica parado e a UI identifica que a ação específica está pendente. Os destinos `JOGOS*` e `WC*` são apenas marcações de áreas futuras, não salas concluídas no PixelLab. O backend prevalece sobre a demonstração se registrar atividade real.

Consulte `docs/PLANO_INTERACOES_ESCRITORIO.md` para a sequência de novos sprites e ambientes.


### Modo tempo livre demonstrativo

O botão **☕** ativa ou desativa uma **SIMULAÇÃO VISUAL**, desligada por padrão. Quando o usuário ativa a opção, apenas agentes com status de backend `nao_conectado`, `aguardando` ou `concluido` fazem passeios sequenciais (um por vez) até os pontos provisórios. Eles usam `walk`, descansam em `idle` e voltam à mesa. Novas tarefas reais ou erros cancelam o passeio. Os eventos do backend permanecem como única fonte de verdade, e nada é enviado à API PixelLab.

Essa opção não realiza as ações reais de beber/jogar/cantar e não significa que um agente está trabalhando. `prefers-reduced-motion` continua aplicando frame estático; as ações específicas e objetos seguem pendentes.

## Estrutura de gestão de vídeo (dados planejados)

O snapshot público contém `organizacao` derivada de `agentes/equipe.json`: cinco departamentos, 27 especialistas planejados e identificação do gerente humano. Os oito cargos anteriores continuam como postos visuais; a seleção de um líder exibe a contagem de subordinados lógicos. **Não são 27 IAs online**, e o site continua sem executar o pipeline. Veja `docs/EQUIPE_PRODUCAO.md`.

### Previsualização de animações extras

Os seis spritesheets básicos continuam sendo carregados ao abrir o escritório. O carregador `site/agent-animator.js` também suporta o manifesto `assets/pixellab/agents/alex/production/manifest.json`, quando disponível. Animações adicionais são **carregadas sob demanda**, para não descarregar dezenas de MB no celular. O painel permite escolher e testar uma delas no agente selecionado, sem alterar o status real de trabalho. Enquanto a exportação do PixelLab não concluir, essa seleção fica oculta.


## Sincronização incremental de sprites extras

O GitHub recebe sprites extras do Alex e imagens de móveis pela action de importação `pixellab-production-import.yml`. O importador gera atlases `agents/alex/production/*.png` e um manifesto com hash e direções para **todos os movimentos já validados**, mesmo se o lote de geração terminar parcialmente. Os seis movimentos básicos não são alterados. A visualização carrega cada sprite extra sob demanda e escolhe uma direção válida para a prévia, sem indicar trabalho real do backend.

Cadeira e armário são recebidos na pasta `objects/production/` com arquivos PNG e manifesto próprio. Esses assets não substituem automaticamente o sprite de cadeira já usado no cenário; ainda é necessário ligar estados/frames ao Canvas após revisão visual.

### Correções das animações por profissão

O botão 🎬 ativa prévia visual dos oito papéis; o backend não é afetado e os status continuam sendo exibidos com o valor real. O botão de conversar com colega leva dois agents à sala criativa e alterna fala/escuta por sprites já importados. O teste de layout impede personagens sobre as janelas e etiquetas invadindo as fileiras.

## Caminhada fluida no Pixel Studio

O motor agora usa os sprites existentes de `walk`, mas redesenha a posição a **30 FPS durante trajetos** (em vez de 10 FPS) e reduz a velocidade de 160 para 112 pixels de mundo por segundo. A fase da passada é individual e avança por 14 px percorridos, independentemente do relógio global; curvas de corredor são arredondadas com pontos de Bézier, e a direção final permanece ao parar. Fora de rotas, a taxa de renderização continua reduzida, respeitando `prefers-reduced-motion`.

Isso suaviza a **movimentação do Canvas**, não aumenta o número de quadros pintados no PNG original (quatro). Nenhum crédito PixelLab é usado. O passeio continua uma prévia visual, não execução real de agents.

## Atualização de caminhada do Alex

O utilitário `scripts/refresh_pixellab_walk.py` aceita por GET a exportação do PixelLab e só substitui `site/assets/pixellab/agents/alex/walk.png` quando há uma variante nova completa (8 direções, 4 frames, 88×88 RGBA, personagem aprovado) ou uma versão atualizada de `walk`. Atualiza o SHA-256 do manifesto. Se faltar quadro ou o conteúdo for igual, mantém o anterior. Os agentes continuam usando o nome lógico `walk`, então a troca alcança todos os trajetos, sem alterar os status reais nem iniciar geração paga. O workflow `pixellab-walk-upgrade.yml` faz a sincronização e publica Pages somente após substituição verificada.


### Walking PixMinimax com 8 frames por direção (10/11/2026)

A captura fornecida confirmou 8 quadros por direção em `walking`. O atlas básico `walk.png` deve usar 8×8 frames (704×704 px) quando houver os 64 PNGs completos no ZIP PixelLab. A propriedade `motions.walk.frames=8` e a largura `704` substituem o antigo pressuposto de 4 frames; os outros cinco movimentos básicos continuam com 4 quadros. O Canvas detecta a contagem por movimento e as rotinas mantêm o mesmo comprimento de ciclo de caminhada (56 px), usando passos de 7 px com 8 frames. Exportações incompletas não substituem o último atlas validado. O workflow de atualização faz apenas GET, executa testes e publica Pages quando um atlas novo é realmente versionado. Não altera estados reais dos agentes e não gera novas imagens pagas.
