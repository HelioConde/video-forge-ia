# Canais

Esta pasta guarda **um diretório por canal**. O primeiro é `exemplo` (não está ligado a uma conta real do YouTube).

```text
canal/
├── README.md
└── exemplo/
    ├── canal.json                 # preferências e modelo padrão deste canal
    └── videos/
        └── teste-10s/
            └── video.json        # roteiro, cenas e modelo opcional do vídeo
```

## Regra de herança do modelo

- Um canal escolhe o seu `modelo_padrao` em `canal/<id>/canal.json`.
- Cada vídeo pode usar `"modelo": "outro-modelo"` em `video.json` para substituir o padrão.
- Os modelos disponíveis ficam em `modelos/<id>/modelo.json`. Alterar a escolha de um vídeo não altera os demais.
- Se o modelo selecionado não existir, a validação falha. Não há fallback silencioso para um modelo errado.

Para adicionar outro canal, copie a pasta `exemplo`, altere seu `id` e suas configurações. Para adicionar um vídeo, crie `videos/<id>/video.json` no canal correspondente.

**A pasta `canal/` guarda configurações e roteiros.** Arquivos MP4, áudio e imagens gerados devem ficar em `output/` (ignorada pelo Git), evitando o crescimento do repositório.
