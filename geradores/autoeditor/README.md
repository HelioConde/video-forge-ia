# Gerador AutoEditor — motor original integrado ao VideoForge AI

Este é um gerador **reutilizável para qualquer canal/nicho**, inspirado no
pipeline real do repositório [AutoEditorVideo](https://github.com/HelioConde/AutoEditorVideo).
Não substitui Kids, Anime, Dorama ou outros geradores: o canal ou vídeo
pode optar por este motor quando preferir esse formato de edição.

## O que funciona no executor

1. Recebe um manifesto editorial criado pelos agentes e validado pelo VideoForge:
   título, canal, idioma, roteiro dividido em cenas e prompts das imagens.
2. **Edge Neural TTS**, como no AutoEditor, produz narração MP3 e marcações reais
   `WordBoundary`. Se os marcadores ou a duração falharem, o job para.
3. Somente após a voz passar, o cliente `videoforge/proxy/client.py` solicita
   **uma imagem por cena via `gpt-image-2` ao Codex Proxy**. Sem imagem manual
   do ChatGPT, arte feita por Pillow ou fallback local. HTTP 429 interrompe.
4. Valida hashes, formatos e origem pela política global
   `videoforge/production/image_policy.py`.
5. Usa **o código Remotion original de AutoEditorVideo**, composição
   `ArquivoOtakuMaster` em `motion-remotion/src/master-short.tsx`:
   cenas com movimento de câmera, transições e legendas sincronizadas
   pelas marcações reais das palavras. Esse modo **não** é rigging independente
   de personagens e não deve ser descrito como tal.
6. Confere MP4 real com FFprobe, áudio, 1080×1920, aproximadamente 30 FPS,
   duração de 90–180s e SHA256. Produz relatório de QA **pendente**;
   não faz upload ou agendamento no YouTube.

O motor Remotion é retirado de
`HelioConde/AutoEditorVideo@ec85db5bc74455122e4501aba05bd2dd3fd0df2c`,
e o Go Proxy de
`10/chatgpt-codex-proxy@1da5476e46ef62830d7016de2a931b0b8270a6c4`.
Pinos explícitos protegem contra mudanças inesperadas nas dependências.

**Diferença do original:** não importamos seus scripts históricos de upload,
lotes diários ou configurações específicas de Death Note/Fofinhos.
A integração reutiliza o renderizador original, a abordagem de Edge TTS,
cortes e a estratégia de imagens. As tarefas editoriais continuam nos
agentes do VideoForge; o motor não inventa roteiro nem dados do YouTube.

## Teste sem IA e sem custos

Execute na raiz do repositório:

```powershell
python -m videoforge.generators.autoeditor --action plan --manifest geradores/autoeditor/exemplo-manifesto.json --output output/autoeditor-plan.json
python -m unittest discover -s tests -p 'test_autoeditor_generator.py' -v
```

O exemplo é uma história fictícia original com oito cenas, **apenas uma
entrada de demonstração**; nenhuma imagem foi criada pelo assistente.

## Gerar um vídeo real (opt-in)

No GitHub > Actions > **VideoForge - Gerador AutoEditor (plano ou video privado)**:

- `action=plan`: valida o manifesto e gera um plano para baixar,
  **sem usar secrets, IA ou TTS**;
- `action=render`: requer `authorize_render=true`, branch `main`,
  primeiro attempt e Environment protegido `proxy-runtime`;
- `manifest` aponta para um arquivo JSON versionado em `geradores/` ou
  `canal/`. O exemplo serve somente quando o roteiro TTS atingir
  90–180s reais; caso contrário para antes de qualquer imagem;
- o gerador não possui credenciais de YouTube e não faz upload;
- o vídeo e as imagens ficam em um artifact do Actions por **sete dias**
  para revisão visual humana; não devem ser publicados sem QA.

O render manual pode utilizar até **12 chamadas de imagem** por tentativa,
limitadas a uma por cena e sem retry automático, usando a mesma conta
Codex Proxy configurada anteriormente. O modelo pode retornar HTTP 429
ou estar sem quota: **o workflow falha, sem imagem substituta**.
Não executar repetidamente para contornar limites.

## Formato do manifesto

`geradores/autoeditor/exemplo-manifesto.json` é a referência:
`schema: videoforge/autoeditor-job/v1`, `canal`, `id`, `titulo`, `descricao`,
`idioma`, `voz`, `formato: short-90s`, `feito_para_criancas`,
`modelo_imagem: gpt-image-2`,
`origem_imagens: integrated-image-generator`,
`aprovacao_humana_obrigatoria: true`,
`upload_habilitado: false`, e de 3 a 12 `cenas`.
Cada cena tem `id`, `papel`, `narracao` e `prompt_imagem`.

O vídeo só é finalizado após obter **todas** as imagens e passar FFprobe.
O manifesto e os recursos não são provas de direitos autorais nem de
consistência visual; a aprovação editorial exige inspeção humana.

## Próximas extensões sem misturar nichos

Os geradores Kids e Dorama podem reutilizar este mesmo motor de voz,
imagens e Remotion quando for apropriado, mas conservam seus próprios
fluxos para personagens em camadas, continuidade, interação e QA.
Para usar animação realmente articulada, integrar um perfil técnico de
camadas próprio; **não chamar zoom/pan de animação de personagem**.

Este gerador pode ser escolhido por vídeo sem alterar
`canal.json.gerador_padrao` nem `modelo_padrao`. Não há lista de gêneros
fixa no código.
