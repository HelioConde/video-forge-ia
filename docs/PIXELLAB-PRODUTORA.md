# VideoForge AI — Produção de animações para a equipe

## Como solicitar e gerar animações para a grande produtora

O catálogo completo está em `personagens/alex/production-animations.json` (137 ações propostas, incluindo ações de personagem, sequências reaproveitáveis e objetos). O motor `videoforge/pixellab/production_animations.py` executa somente as do tipo `character`, aproveitando grupos e direções já presentes no PixelLab.

A ação `pixellab-production-plan.yml` consulta a biblioteca (GET), produz relatório sem IDs privados e testa o grafo de delegação. Não cobra créditos. A geração utiliza a mesma base Alex validada por impressão digital; nunca recria o personagem.

As animações de trabalho poderão ser vinculadas às tarefas do backend **somente depois** que existirem sprites reais e que os executores começarem a emitir eventos verificados. O catálogo não transforma os 27 especialistas em processos IA ativos e não autoriza publicação de vídeos.

Existem limitações técnicas: uma ação longa pode exigir mais de quatro frames, objetos independentes e transições de início/fim. Sequências compostas como `approach_person` reutilizam `walk`; objetos como cadeira que gira e armário que abre precisam de endpoints de objetos, não da rota de personagens. Essa integração fica em etapa separada.

Os lotes pagos devem informar um número máximo de chamadas, ter aprovação, salvar relatório de progresso e parar em caso de timeout, crédito insuficiente, resposta ambígua ou falha de qualidade. Não repetir POSTs cobrados no escuro. A referência de preços v3 64×64 é indicativa, não um teto de cobrança: https://www.pixellab.ai/pixellab-api.

## Produção solicitada: execução de lote

O usuário autorizou a criação de **todas as animações listadas e necessárias**. O catálogo possui 137 entradas, das quais 122 são movimentos de personagem (145 pares movimento+direção) e 15 são sequências ou movimentos de objetos que exigem implementação própria.

- `.github/workflows/pixellab-production-first.yml` executa **até seis POSTs pagos** iniciais e valida os quatro frames por direção na exportação real.
- `.github/workflows/pixellab-production-continue.yml` só é acionado por conclusão **bem-sucedida** da etapa inicial, sob a trava `pixellab-personagens`; consulta novamente a biblioteca antes de cada POST, com limite de **145 novas direções**.
- A produção é sequencial e pode demorar; o GitHub Actions tem timeout de 350 minutos. Não confundir `in_progress` com concluído.
- Falta de créditos, timeouts, grupos ambíguos, frames ausentes ou falhas da API interrompem o fluxo sem reenvio automático do POST. Reavaliar antes de reiniciar.
- O PixelLab persiste os frames; o GitHub guarda apenas relatórios saneados por sete dias. **Novos atlases não são importados automaticamente para o Pages**, pois precisam de revisão visual de qualidade.
- Objetos independentes (como cadeira girando e armário) e sequências compostas serão implementados em outras rotas/workflows. O motor de personagens não deve fingir que criou esses recursos.
- Os custos são variáveis. A referência pública informa que v3 com quatro frames e 64×64 custa aproximadamente USD 0,0129 por direção; essa referência **não** é uma garantia de preço ou teto de faturamento. <https://www.pixellab.ai/pixellab-api>.

## Importação dos sprites novos para o repositório

Depois da conclusão bem-sucedida de `pixellab-production-continue.yml`, o workflow `pixellab-production-import.yml` baixa por GET o ZIP do personagem, valida a origem e a presença dos **145 pares movimento/direção** e converte os frames em 122 atlases `site/assets/pixellab/agents/alex/production/<motion>.png` com manifesto de hashes e dimensões. Não transfere o ZIP nem metadados privados para o Git.

Esse workflow falha se qualquer frame estiver ausente/vazio e **não comita atlas parciais**. Publicar os PNGs no repositório não muda automaticamente o comportamento dos agentes; adicionar uma animação ao Canvas depende da interação e dos estados de UI.

## Móveis animados

A auditoria `pixellab-production-object-audit.yml` confirmou cadeira existente sem animações de giro e ausência do armário. A ação pontual `pixellab-production-objects.yml` usa a biblioteca `objects` e executa no máximo **quatro POSTs pagos**: `rotate_chair_left`, `rotate_chair_right`, criação do armário se ainda não existir e `open_cabinet`. Não cria nova cadeira nem repete animações existentes. Usa a trava `pixellab-personagens` para não executar simultaneamente ao lote grande do Alex. Resultado fica no PixelLab; o GitHub recebe somente relatório saneado. Novas imagens de móveis ainda precisam de exportação e aprovação antes de usar no site.


## Recebedor automático de todas as imagens — atualização

O importador agora aceita **lotes parciais**: uma animação só entra quando **todos os seus frames/direções definidos no catálogo** estiverem presentes e validados; os movimentos anteriores são preservados se o ZIP da próxima leitura estiver incompleto. Se o workflow longo falhar ou atingir timeout, a importação tenta recuperar somente os movimentos já concluídos por GET. Sem repetir POST, sem geração de custos ou duplicatas. O arquivo `site/assets/pixellab/agents/alex/production/manifest.json` informa a contagem disponível/pendente e contém apenas campos seguros.

A recepção inclui objetos: `site/assets/pixellab/objects/production/manifest.json`, com imagens de spritesheet e prévias da cadeira e do armário, sem sobrescrever objetos aprovados do cenário. A API PixelLab oferece `GET /objects/{id}/spritesheet`, que exige Bearer; o cliente remove a credencial em qualquer redirecionamento para armazenamento. Layouts privados e ZIPs temporários nunca entram no Git. O site continua usando os seis movimentos básicos quando não existem sprites extras.

Para sincronizar manualmente sem custo de geração: **Actions → PixelLab - Receber todas as imagens no GitHub → Run workflow**, escolher `todas`, `alex` ou `objetos`. Quando os workflows `Completar animacoes da produtora` ou `Objetos animados da produtora` terminarem, a sincronização também dispara automaticamente. O workflow revalida os PNGs antes de qualquer commit e o Pages publica somente o que passou na validação.


### Publicação do GitHub Pages após importação de PNGs

Commits criados por GitHub Actions usando `GITHUB_TOKEN` não disparam novos workflows `on: push`. Portanto o recebedor verifica se houve mudança, faz commit dos PNGs aprovados e **chama diretamente o workflow reutilizável** `.github/workflows/pages.yml` por `workflow_call`. O Pages usa checkout de `main` para receber os PNGs importados, em vez de uma revisão anterior do workflow que iniciou o processo. Se não houver arquivos novos, o recebedor não força deploy desnecessário.

## Caminhada corrigida pelo gerente — estado walk, não Idle

O gerente substituiu manualmente a caminhada no PixelLab. O importador `scripts/refresh_pixellab_walk.py` **seleciona exclusivamente o grupo `walking` do estado `walk`** no ZIP do Alex, jamais a animação de mesmo nome sob `Idle` ou outra variante. O estado `walk` precisa conter 8 direções × 8 quadros RGBA 88×88. Se faltar o estado ou um frame, preserva o atlas anterior e relata a pendência; não retorna à versão que o gerente rejeitou. O manifesto inclui `sourceState: walk` para auditoria. A action `pixellab-walk-upgrade.yml` roda essa correção por GET sem gerar novas imagens pagas e publica Pages somente depois de validar um novo atlas.

### Dimensão variável dos frames

O estado `walk` escolhido pelo gerente exporta quadros **92×92**, diferentes da base original do Alex (**88×88**). O importador calcula a dimensão real sem cortar, redimensionar ou descartar pixels, registra `motions.walk.frameWidth/frameHeight` e monta 8 direções × 8 frames. O Canvas extrai cada quadro com as dimensões do manifesto, mantendo a escala visual das estações. Outras animações básicas continuam com 88×88. 
