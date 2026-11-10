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
