# Arquitetura proposta — VideoForge AI

## Organização por canal e por modelo

```text
canal/
  <canal-id>/
    canal.json
    videos/
      <video-id>/
        video.json
modelos/
  <modelo-id>/
    modelo.json
videoforge/
  config.py     # resolve a receita do canal/vídeo
  pipeline.py   # prepara e valida storyboard (dry-run)
tests/
.github/workflows/
output/         # gerados localmente, fora do Git
```

- **Canal**: define idioma, configurações de publicação e `modelo_padrao`.
- **Vídeo**: guarda duração, roteiro/cenas e `modelo` opcional. Quando existe, substitui o modelo padrão do canal.
- **Modelo de produção**: receita independente do canal para etapas de roteiro, imagem, animação, voz e montagem.
- **Modelo de IA**: provedor e identificação configuráveis para cada etapa (`provedor` e `modelo_ia`), ainda não integrados.

## Padrão obrigatório de organização e manutenção contínua

**Regra permanente: toda implementação, manutenção, correção, experimento ou refatoração deve deixar o projeto organizado.** Nenhuma funcionalidade deve ser considerada concluída se introduzir desordem estrutural, duplicação desnecessária ou documentação desatualizada.

### Responsabilidades por local

| Caminho | Responsabilidade |
| --- | --- |
| `canal/<id>/canal.json` | Configurações próprias do canal e modelo padrão |
| `canal/<id>/videos/<id>/video.json` | Definição de cada vídeo e seleção opcional de modelo |
| `modelos/<id>/modelo.json` | Receitas reutilizáveis de produção e opções de IA |
| `videoforge/` | Código reutilizável de orquestração, configuração e módulos de produção |
| `tests/` | Testes correspondentes aos comportamentos implementados |
| `.github/workflows/` | Pipelines de CI e agendamento, sem lógica de negócio duplicada |
| `docs/` | Documentação de arquitetura, decisões e procedimentos |
| `output/` | Saídas geradas, logs e mídias locais; conteúdo não versionado |

### Checklist obrigatório para cada mudança

1. **Antes:** inspecionar os diretórios e os módulos afetados; aproveitar os componentes existentes antes de criar outros.
2. **Durante:** colocar cada arquivo na pasta de sua responsabilidade, manter nomes claros, funções coesas e interfaces estáveis.
3. **Isolamento:** não misturar configurações, assets nem credenciais entre canais; herança de modelo por vídeo precisa continuar funcionando.
4. **Limpeza:** evitar arquivos descartáveis ou duplicados; só apagar conteúdo após confirmar que não é utilizado.
5. **Depois:** atualizar README/documentação e exemplos quando houver mudança de comportamento, executar testes e inspecionar a estrutura final.
6. **Integração:** manter os workflows organizados e validar que automações novas não substituam ou quebrem as existentes.

As regras também estão resumidas no [README principal](../README.md) e devem ser seguidas por agentes conforme [AGENTS.md](../AGENTS.md).

## Catálogo de canais herdado do AutoEditorVideo

| Pasta | Chave legada | Modelo inicial |
| --- | --- | --- |
| `canal/otaku-br/` | `br` | `camadas-animadas` |
| `canal/otaku-en/` | `en` | `imagem-estatica` |
| `canal/gamer/` | `games` | `imagem-estatica` |
| `canal/manu-kids/` | `kids` | `camadas-animadas` |
| `canal/alchemy-lab/` | `alchemy` | `imagem-estatica` |

Os padrões são provisórios. Os arquivos em `arquivo-editorial/` são referências e não scripts de publicação. O teste de 10 segundos agora fica em `canal/alchemy-lab/videos/teste-10s/`.

Consulte [MIGRACAO_AUTOEDITORVIDEO.md](MIGRACAO_AUTOEDITORVIDEO.md). Nenhum token ou upload foi migrado.

## Meta

Automatizar: pauta > roteiro > planejamento de cenas > geração de imagens e camadas > animação > narração > montagem > validação > upload no YouTube.

## Módulos planejados

1. **Content Planner**: tema, canal, vídeo, roteiro, storyboard e continuidade dos personagens.
2. **Scene Composer**: imagem completa de referência; extração de cenário, personagens e objetos transparentes.
3. **Animator**: anima os elementos separadamente, preservando enquadramento e identidade.
4. **Audio Studio**: vozes e efeitos licenciados, com sincronização.
5. **Renderer**: renderização FFmpeg com legendas e áudio.
6. **Quality Gate**: duração, consistência, assets ausentes e duplicatas.
7. **YouTube Publisher**: OAuth/YouTube Data API, teste privado antes de liberar publicação.
8. **Scheduler / Observability**: GitHub Actions, logs, recuperações e status de cada canal.

## Etapas de entrega

- [x] Organização de pastas por canal, vídeo e modelo reutilizável.
- [x] Herança de modelo do canal com sobrescrita por vídeo, com testes.
- [x] Storyboard JSON de exemplo e validação no GitHub Actions.
- [ ] Integração real de IA para roteiros, imagens, animação e voz.
- [ ] Renderização de um MP4 de 10 segundos.
- [ ] Upload privado de teste no YouTube.
- [ ] Agendamento automático e monitoramento.

## Segurança e limites atuais

- O protótipo **não gera imagens, áudio ou MP4 e não realiza uploads**.
- Credenciais devem ficar em Actions Secrets, nunca em `canal/` ou `modelos/`.
- Testar em privado primeiro, impedir uploads repetidos, validar qualidade e controlar custo das APIs.

## Estrutura do escritório Pixel Studio

O frontend estático é organizado em `site/`:

- `office-art.js`: desenho original do estúdio e dos personagens, com dados de posição reutilizados pela interação.
- `office-renderer.js`: engine Canvas 2D, câmera, zoom, gestos de toque, hit-testing e minimapa.
- `app.js`: seleção, detalhes dos agentes/canais e consumo seguro do snapshot de status.
- `styles.css` e `index.html`: disposição responsiva, HUD e painéis.
- `data/status.json`: snapshot público gerado pelo backend, sem credenciais.

Os arquivos de arte não executam serviços de IA. A publicação da interface ocorre por GitHub Pages Actions e é independente da publicação de vídeos no YouTube.

## Integração opcional PixelLab

- `personagens/<slug>/profile.json`: descrição e animações próprias de cada personagem.
- `videoforge/pixellab/client.py`: autenticação, APIs PixelLab v2, jobs e exportações.
- `videoforge/pixellab/cli.py`: seleção da base existente ou criação, animações e planejamento seguro.
- `.github/workflows/pixellab-character.yml`: comando manual com controle de custos e divulgação.
- `tests/test_pixellab.py`: testes simulados sem rede.
- `output/pixellab/`: arquivos temporários fora do Git.

A geração de sprites ainda não está conectada ao Canvas nem ao renderizador dos vídeos. Veja `docs/PIXELLAB.md`.

## Orquestração PixelLab em lote para Work

- `videoforge/pixellab/batch.py`: consulta GET a base exata, compara movimentos/direções, reutiliza grupo anterior por ID, limita novas gerações e escreve relatório público sem UUID.
- `.github/workflows/pixellab-work.yml`: workflow manual para o ChatGPT Work, com modos planejar/gerar, autorização de custo/exposição, trava `pixellab-personagens` e máximo de oito POSTs por disparo.
- `tests/test_pixellab_batch.py`: simulações sem API paga, cobrindo reuso, antduplicação, bloqueios e exportações.
- `docs/PIXELLAB-WORK.md`: operação, parâmetros e procedimento de retomada segura.

A fonte de verdade dos movimentos continua sendo a conta PixelLab; o GitHub armazena apenas relatório de execução e ZIPs opcionais por sete dias, nunca segredos ou mídias geradas permanentemente no Git.

## Cenários e objetos do Pixel Studio gerados no PixelLab

O catálogo `cenarios/escritorio/pixellab-plan.json` descreve três salas e seis objetos em paleta coerente. O módulo `videoforge/pixellab/office_assets.py` faz auditoria paginada, controla custos por limite de POSTs, salva status saneado e exporta PNGs quando URLs de prévia confiáveis estiverem disponíveis. As bibliotecas Rooms e Objects do PixelLab são fonte de verdade; não criar mídia versionada.

Workflows: `pixellab-office-audit.yml` (somente GET), `pixellab-office-start.yml` (uma sala e dois objetos), `pixellab-office-continue.yml` (duas salas e quatro objetos, condicionado ao sucesso do primeiro). Validar com `tests/test_pixellab_office.py`. Arte visual só é ligada ao Canvas após inspeção das imagens. Ver `docs/PIXELLAB-OFFICE.md`.

## Publicação dos sprites PixelLab para o Canvas

As nove imagens aprovadas foram copiadas dos artifacts das Actions para `site/assets/pixellab/` em um único importador com validação de PNG, dimensões, hash e ausência de dados de conta. O manifesto local registra `sha256`, sem IDs ou URLs privadas de PixelLab. O desenho de cenas no Canvas continua concentrado em `site/office-art.js`; o renderizador `site/office-renderer.js` só controla carregamento/viewport/seleção, e `site/app.js` controla o botão de modo. Falhas de carga preservam a arte anterior. O site é estático e não chama PixelLab em tempo de execução.

## Animação de agentes a partir dos sprites do PixelLab

O workflow `.github/workflows/pixellab-export-alex.yml` exporta os frames sem gerar novamente; `scripts/import_pixellab_agents.py` converte o ZIP validado em atlas PNG, eliminando todos os metadados privados; a action `.github/workflows/pixellab-import-alex.yml` salva os arquivos no repositório. O manifesto `site/assets/pixellab/agents/alex/manifest.json` guarda apenas direções, movimentos, dimensões e hashes. O carregador `site/agent-animator.js` valida seis atlas de 352×704 e desenha sincronicamente no Canvas com suporte a `prefers-reduced-motion`. `site/office-art.js` faz a seleção de animação por status backend e `site/office-renderer.js` mantém apenas câmera, render e hit-testing. Falha ao importar qualquer atlas não impede a arte anterior.

## Locomoção visual e interação com cenários

`site/agent-routines.js` mantém somente rotas de demonstração em memória do navegador. A biblioteca de destinos limita as ações a café, água, jogos, entrada do banheiro e retorno à estação; não altera `status` do backend, não faz solicitações à API PixelLab e não exibe consumo de recursos inexistentes. O Canvas `office-art.js` utiliza a mesma posição/direção calculada para `walk` e `idle`, `office-renderer.js` aplica o mesmo deslocamento a hit-testing e minimapa, e `app.js` oferece comandos explicitamente rotulados como prévia. Não confundir com robôs operacionais ou uma simulação persistente de trabalho.

## Gestão, delegação e novas animações da produtora

`agentes/equipe.json` v2 preserva oito cargos visuais e acrescenta estrutura hierárquica (`manager`, `departamentos`, especialistas lógicos desativados). O exportador `scripts/build_dashboard_data.py` publica apenas contagens e nomes de departamentos como `organizacao`. No painel, as relações são marcadas como planejadas; não inventar execução real.

`videoforge/production/dispatcher.py` cria o DAG de 18 tarefas por demanda; as atividades são apenas `blocked` ou `ready` até haver artefato validado. Não executa IA/pagamento/publicação. `personagens/alex/production-animations.json` contém 137 ações categorizadas em `character`, `sequence` e `object`. O motor `videoforge/pixellab/production_animations.py` só paga por direções de personagem ausentes após verificar GET e autorização, sem guardar IDs privados nos artefatos; novos sprites precisarão de revisão visual antes de entrar no Canvas.

### Atlas extras da produtora e carregamento tardio

A action `pixellab-production-import.yml` transforma a exportação do PixelLab em atlases PNG e manifesto de produção, sem UUIDs. O carregador do Canvas lê o manifesto como recurso opcional e só busca a animação escolhida pelo usuário; nenhuma animação nova é simulada enquanto o arquivo não estiver presente. Os seis atlas originais e o fallback anterior permanecem inalterados. Os movimentos extras são usados apenas como **prévia visual** até os eventos reais dos especialistas serem conectados.


## Recepção incremental e versionamento das imagens PixelLab

O workflow de importação `.github/workflows/pixellab-production-import.yml` é acionado após a conclusão dos lotes PixelLab de personagens e objetos (inclusive em caso de falha de geração, para aproveitar sprites completos), ou por `workflow_dispatch`. Ele usa **somente GET** e armazenamento temporário para os ZIPs; nenhuma mídia bruta, UUID, prompt, token, URL assinada ou metadado privado é commitado. A mesma trava de concorrência da recepção serializa as alterações no Git.

`scripts/import_pixellab_production.py` recebe os frames do Alex, confere a identidade do personagem, valida PNGs RGBA de 88×88, monta spritesheets de quatro quadros e preserva movimentos já importados quando a exportação nova está parcial. O manifesto público informa o total de movimentos disponíveis/pendentes.

`scripts/import_pixellab_objects.py` lê a biblioteca de objetos e o ZIP autenticado de spritesheet por meio de `PixelLabClient.download_object_spritesheet`. Somente os PNGs sanificados da cadeira e armário são versionados sob `site/assets/pixellab/objects/production/`. URLs e layouts originais da API não entram no site. Uma imagem de objeto importada não é interpretada como animação conectada até receber mapeamento visual/âncoras. `scripts/verify_pixellab_assets.py` confere assinaturas PNG, tamanhos, hashes e caminhos antes do commit. O trigger `site/**` do Pages realiza o deploy após cada alteração validada.


### Propagação confiável das imagens importadas ao Pages

O `GITHUB_TOKEN` não reativa workflows via `push` quando um próprio Actions faz commit. O recebedor possui saída `imagens_alteradas` e invoca a publicação via `workflow_call` somente se novos PNGs/manifests forem versionados. O workflow Pages é reutilizável e faz checkout explícito de `main` para publicar a revisão que contém as mídias aprovadas. Esta chamada não executa IA nem publica vídeos em canais.

## Movimentos profissionais e alinhamento de agents

O catálogo de animações especializadas é consumido pelo `site/agent-behavior.js` sem duplicação de nomes no renderizador. O Canvas seleciona as ações por cargo e status do backend; a prévia 🎬 permanece opt-in para funções não conectadas. `site/agent-routines.js` controla a demonstração de conversas e o deslocamento aos pontos da reunião. Slots e placas da sala PixelLab foram reposicionados e validados em `tests/test_office_layout.js`. Nenhuma chamada paga ou publicação de vídeos foi acionada. Consulte `docs/CORRECOES_AGENTS.md`.

### Passada e interpolação dos agents

O `site/agent-routines.js` retorna `poseFor(id, t)` com posição contínua, direção, distância acumulada e `frame` próprio para `walk`. Usa velocidade de 112 px/s, 14 px por troca de frame e curvas quadráticas curtas no corredor, sem modificar status reais. `hasMoving(t)` habilita o modo de 30 FPS em `site/office-renderer.js` apenas durante deslocamentos; `site/office-art.js` seleciona o quadro individual em vez de sincronizar todos os agents pelo relógio global. Mantêm-se os quatro frames existentes no PixelLab, sem novas chamadas pagas. Testes: `node tests/test_agent_routines.js`; CI do site e Playwright desktop/mobile.

## Atualização de caminhada do Alex

O utilitário `scripts/refresh_pixellab_walk.py` aceita por GET a exportação do PixelLab e só substitui `site/assets/pixellab/agents/alex/walk.png` quando há uma variante nova completa (8 direções, 4 frames, 88×88 RGBA, personagem aprovado) ou uma versão atualizada de `walk`. Atualiza o SHA-256 do manifesto. Se faltar quadro ou o conteúdo for igual, mantém o anterior. Os agentes continuam usando o nome lógico `walk`, então a troca alcança todos os trajetos, sem alterar os status reais nem iniciar geração paga. O workflow `pixellab-walk-upgrade.yml` faz a sincronização e publica Pages somente após substituição verificada.


### Walking PixMinimax com 8 frames por direção (10/11/2026)

A captura fornecida confirmou 8 quadros por direção em `walking`. O atlas básico `walk.png` deve usar 8×8 frames (704×704 px) quando houver os 64 PNGs completos no ZIP PixelLab. A propriedade `motions.walk.frames=8` e a largura `704` substituem o antigo pressuposto de 4 frames; os outros cinco movimentos básicos continuam com 4 quadros. O Canvas detecta a contagem por movimento e as rotinas mantêm o mesmo comprimento de ciclo de caminhada (56 px), usando passos de 7 px com 8 frames. Exportações incompletas não substituem o último atlas validado. O workflow de atualização faz apenas GET, executa testes e publica Pages quando um atlas novo é realmente versionado. Não altera estados reais dos agentes e não gera novas imagens pagas.
