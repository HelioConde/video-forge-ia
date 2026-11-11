# Agência unificada — geração de cenário PixelLab

## Objetivo

Gerar com **a integração PixelLab v2 existente** um único cenário da sede da VideoForge AI inspirado na imagem de referência aprovada. Não repetir o antigo padrão de três salas PixelLab isoladas. O cenário será **uma única planta** com piso conectado, ambientes reconhecíveis e espaço para os oito agentes animados, sem pessoas desenhadas dentro do fundo.

## Arquivos

- [Plano e prompt](../cenarios/escritorio/agencia-unificada.json)
- [Referência de composição](../cenarios/escritorio/referencias/agencia-unificada.png) — redução **128×72 PNG** da imagem gerada na conversa, usada como orientação de layout e paleta; o gerador não trata isso como sprite final.
- [Programa](../videoforge/pixellab/agency_scene.py) — reutiliza o PixelLabClient e chama apenas \`/generate-image-v2\` na geração; inclui \`reference_images\`, \`style_image\`, e a descrição em inglês.
- [Workflow GitHub Actions](../.github/workflows/pixellab-agency-scene.yml)
- [Testes sem cobrança](../tests/test_pixellab_agency.py)

A resolução solicitada ao modelo é **688×384 (16:9)**. O Canvas atual possui mundo 1280×820; portanto a arte PixelLab precisa de revisão, redimensionamento proporcional e reavaliação das âncoras antes de integração. A referência de 128×72 tem largura reduzida para ser compatível com geração em pixel art nativa. O original gerado na conversa não foi usado como resultado final do PixelLab.

## Etapas de uso

1. Executar o workflow **PixelLab - Gerar agencia unificada (referencia visual)**, modo \`plan\`: gratuito, valida a referência e o contrato. No branch de desenvolvimento, o push roda exclusivamente esse modo. Não precisa de Secret.
2. Revisar créditos, preços atualizados e o plano. **Nenhum valor foi debitado pelo modo plan.**
3. Para gerar uma imagem, selecionar \`generate\` manualmente e marcar explicitamente as duas confirmações: **consumo de créditos para uma geração** e **visibilidade do artifact público**. O workflow usa \`PIXELLAB_API_TOKEN\` em GitHub Secrets e faz **no máximo um POST**, com mutex de concorrência.
4. Baixar o artifact \`pixellab-agencia-unificada-<run_id>\` da Actions: inclui \`report.json\` e, se o job concluir com PNG, \`scene.png\`. O arquivo fica disponível 7 dias. Não expõe token, ID privado ou URLs de mídia.
5. **Aprovar visualmente** antes de importar como \`site/assets/pixellab/scenes/agencia-unificada.png\`, ajustar o Canvas e recalibrar os postos/rotas no \`site/office-map.js\`. A cena não muda o site automaticamente; a imagem deve ser conferida para evitar caracteres distorcidos ou estrutura impraticável.

## Conteúdo solicitado no prompt

- Uma só sede com entrada central, iluminação quente, janelas e piso de madeira contínuo
- Produção (Direção, Roteirista, Revisor, Publicador)
- Sala criativa (Artista visual e Animador)
- Áudio e edição (Narrador e Editor)
- Mesa de reunião central compartilhada, copa e água, lazer/jogos e WC
- Corredores internos navegáveis, plantas, divisórias baixas; nada de mini-prédios
- **Sem personagens, placas em texto, labels ou HUD** na imagem gerada: o Canvas desenha agentes, nomes e interface separadamente

## Segurança e retomada

\`plan\` não constrói nem envia request de geração. \`generate\` exige **duas autorizações explícitas** antes de construir o cliente com o Secret; executa apenas \`POST /generate-image-v2\` uma vez e consulta \`GET /background-jobs/{id}\`. Falha, resposta inesperada ou timeout são motivo para **inspecionar primeiro o job no PixelLab**, não repetir cobrança. PNG retornado é validado por assinatura, tamanho e dimensão antes de salvar no artifact.

Os arquivos aprovados do cenário anterior, os objetos transparentes e os sprites do Alex **não são apagados nem sobrescritos**. A seleção de funcionários, o minimapa e suas animações continuam usando a cena publicada atual até a aprovação da nova arte.
