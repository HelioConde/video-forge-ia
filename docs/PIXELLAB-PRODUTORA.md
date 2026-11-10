# VideoForge AI — Produção de animações para a equipe

## Como solicitar e gerar animações para a grande produtora

O catálogo completo está em `personagens/alex/production-animations.json` (137 ações propostas, incluindo ações de personagem, sequências reaproveitáveis e objetos). O motor `videoforge/pixellab/production_animations.py` executa somente as do tipo `character`, aproveitando grupos e direções já presentes no PixelLab.

A ação `pixellab-production-plan.yml` consulta a biblioteca (GET), produz relatório sem IDs privados e testa o grafo de delegação. Não cobra créditos. A geração utiliza a mesma base Alex validada por impressão digital; nunca recria o personagem.

As animações de trabalho poderão ser vinculadas às tarefas do backend **somente depois** que existirem sprites reais e que os executores começarem a emitir eventos verificados. O catálogo não transforma os 27 especialistas em processos IA ativos e não autoriza publicação de vídeos.

Existem limitações técnicas: uma ação longa pode exigir mais de quatro frames, objetos independentes e transições de início/fim. Sequências compostas como `approach_person` reutilizam `walk`; objetos como cadeira que gira e armário que abre precisam de endpoints de objetos, não da rota de personagens. Essa integração fica em etapa separada.

Os lotes pagos devem informar um número máximo de chamadas, ter aprovação, salvar relatório de progresso e parar em caso de timeout, crédito insuficiente, resposta ambígua ou falha de qualidade. Não repetir POSTs cobrados no escuro. A referência de preços v3 64×64 é indicativa, não um teto de cobrança: https://www.pixellab.ai/pixellab-api.
