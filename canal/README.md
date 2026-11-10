# Canais do VideoForge AI

Cinco canais catalogados do AutoEditorVideo, com isolamento por pasta, regras editoriais e modelo de produção inicial por canal.

| Canal | Pasta | Chave antiga | Modelo padrão inicial | Idioma |
| --- | --- | --- | --- | --- |
| Otaku Multicena | [`otaku-br/`](otaku-br/README.md) | `br` | `camadas-animadas` | `pt-BR` |
| Otaku Reframe | [`otaku-en/`](otaku-en/README.md) | `en` | `imagem-estatica` | `en-US` |
| Conde Games | [`gamer/`](gamer/README.md) | `games` | `imagem-estatica` | `pt-BR` |
| Emanuelly Kids | [`manu-kids/`](manu-kids/README.md) | `kids` | `camadas-animadas` | `pt-BR` |
| Alchemy Lab | [`alchemy-lab/`](alchemy-lab/README.md) | `alchemy` | `imagem-estatica` | `pt-BR` |

Cada canal contém `canal.json`, `README.md`, `conteudos/indice.json` e `videos/README.md`. Alguns terão `arquivo-editorial/` para materiais históricos, que **não** podem ser executados diretamente.

**Modelos padrão são provisórios** e podem ser trocados por canal ou sobrescritos em cada `video.json`. As receitas compartilhadas ficam em [`modelos/`](../modelos/README.md).

## Proteções obrigatórias

- Os cinco uploads estão desabilitados (`conectado=false`, `upload_habilitado=false`, `privacidade=private`).
- Não copiamos tokens, configurações OAuth, nomes de segredos nem workflows de publicação antigos.
- O ID público do YouTube serve apenas para mapear e verificar identidade; não estabelece acesso à conta.
- Os índices são referências editoriais, e os manifestos antigos não são executados pelo novo sistema.
- O AutoEditorVideo não é modificado pela migração.

Veja [o relatório de migração](../docs/MIGRACAO_AUTOEDITORVIDEO.md).
