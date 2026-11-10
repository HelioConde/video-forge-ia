# Pixel Studio — cenários e objetos PixelLab

## Objetivo

Criar arte original de salas e objetos reutilizáveis para o escritório virtual do VideoForge AI, no repositório `HelioConde/video-forte-ia`.

- **3 salas persistentes na biblioteca Rooms** do PixelLab: produção principal, sala criativa, laboratório de mídia.
- **6 objetos persistentes na biblioteca Objects**: mesa com PC, cadeira, planta, estante, mesa de áudio, estação de edição.
- Cores e estilo inspirados no escritório atual `site/office-art.js`: piso de madeira quente, paredes azul-ardósia, acessórios verde-jade, brilho âmbar.
- Os objetos independentes têm `n_directions=1` e tamanho 64 ou 96 px; as salas usam `view=top-down`, tiles de 32 px e portas alinhadas.

Os nomes e prompts ficam em `cenarios/escritorio/pixellab-plan.json`, sem IDs nem credenciais. O módulo `videoforge/pixellab/office_assets.py` centraliza inventário, geração e exportação segura de prévias.

## Como executar

1. A ação [**PixelLab - Inventario de cenarios e objetos**](../.github/workflows/pixellab-office-audit.yml) é gratuita, faz apenas GET e verifica possíveis duplicatas. Resultado inicial: nenhum dos nove assets estava cadastrado.
2. A ação [**PixelLab - Cenarios e Objetos - Inicio**](../.github/workflows/pixellab-office-start.yml) cria **uma sala e dois objetos** (máximo três POSTs pagos), depois de executar os testes.
3. Quando a primeira ação terminar com **sucesso**, a ação [**PixelLab - Cenarios e Objetos - Continuar**](../.github/workflows/pixellab-office-continue.yml) completa as **duas salas e quatro objetos restantes**, limitada a mais seis POSTs pagos.

Ambas utilizam o Secret `PIXELLAB_API_TOKEN` e a mesma trava `pixellab-office-assets`, sem cron. Não recriam conteúdo que já aparece na biblioteca, nem repetem automaticamente operações pagas após erros, timeout, 409 ou status ambíguos.

O fluxo foi autorizado explicitamente pelo usuário em 10 de novembro de 2026 para criar cenários e objetos pelo PixelLab. Estimativas de preço devem ser conferidas na API, pois podem variar.

## Resultados e privacidade

- **Persistência principal:** biblioteca Rooms e Objects da própria conta PixelLab.
- **Relatórios:** `output/pixellab-office/report.json` é armazenado como Artifact no GitHub por 7 dias.
- **Prévia PNG:** quando a API devolver URL de imagem de um host confiável, ela é baixada em `output/pixellab-office/scenes/<slug>.png` ou `objects/<slug>.png` e incluída no Artifact por 7 dias.
- O código evita publicar tokens, UUIDs de assets e URLs privadas nos logs, e não grava mídias geradas no código-fonte.
- As salas e móveis gerados **não são aplicados automaticamente** em `site/office-art.js`: primeiro inspecionar visualmente as imagens e depois adaptar o renderizador ao layout, preservando navegação e Canvas.

## Execução manual local (somente consulta)

```bash
python -m unittest discover -s tests -p 'test_pixellab*.py' -v
PIXELLAB_API_TOKEN=... python -m videoforge.pixellab.office_assets --mode plan
```

Não configurar geração paga em cron ou push geral da branch. Qualquer nova geração deve passar por revisão de inventário e autorização de custo.

[API oficial PixelLab v2](https://api.pixellab.ai/v2/llms.txt).
