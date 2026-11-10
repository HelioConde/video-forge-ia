# Migração dos canais — AutoEditorVideo para VideoForge AI

**Origem:** [HelioConde/AutoEditorVideo](https://github.com/HelioConde/AutoEditorVideo), commit `f87d9f6a9dbcd7340b5ec9973d573fd2fddc5210`, branch `main`.  
**Destino:** [HelioConde/video-forte-ia](https://github.com/HelioConde/video-forte-ia), pasta `canal/`.

## Canais

| Chave antiga | Pasta nova | Nome cadastrado | Nome observado no YouTube |
| --- | --- | --- | --- |
| `br` | `canal/otaku-br/` | Otaku Multicena | Otaku Multicena |
| `en` | `canal/otaku-en/` | Otaku Reframe | Otaku Reframe |
| `games` | `canal/gamer/` | Conde Games | Hélio Conde |
| `kids` | `canal/manu-kids/` | Emanuelly Kids | Emanuelly Kids |
| `alchemy` | `canal/alchemy-lab/` | Alchemy Lab | Alchemy Flames |

## Material importado

- Cinco `canal.json` com configurações editoriais, ID público do YouTube, idioma, público, políticas e modelo padrão **provisório**.
- Um `conteudos/indice.json` por canal com links fixados aos manifestos no AutoEditorVideo; **não são manifestos executáveis do VideoForge**.
- Pastas `arquivo-editorial/` de Otaku Reframe, Emanuelly Kids e Alchemy Lab com cópias históricas selecionadas:
  - `canal/otaku-en/arquivo-editorial/testes-animados-5-en.json` (origem: `conteudos/testes-animados-5-en.json`)
  - `canal/manu-kids/arquivo-editorial/fofinhos-ep01-shortserie-v1.json` (origem: `conteudos/kids-emanuelly-ep01-shortserie-v1.json`)
  - `canal/manu-kids/arquivo-editorial/experimento-12-nichos-20261109.json` (origem: `conteudos/kids-experimento-12-nichos-20261109.json`)
  - `canal/alchemy-lab/arquivo-editorial/conquiste-a-princesa-ou-morra/README.md` (origem: `canais/alchemy-lab/conteudos/conquiste-a-princesa-ou-morra/README.md`)
  - `canal/alchemy-lab/arquivo-editorial/conquiste-a-princesa-ou-morra/episodio-01.json` (origem: `canais/alchemy-lab/conteudos/conquiste-a-princesa-ou-morra/episodio-01.json`)
  - `canal/alchemy-lab/arquivo-editorial/conquiste-a-princesa-ou-morra/referencias-v1.json` (origem: `canais/alchemy-lab/conteudos/conquiste-a-princesa-ou-morra/referencias-v1.json`)
  - `canal/alchemy-lab/arquivo-editorial/piloto-3-nichos-20261109.json` (origem: `conteudos/alchemy-lab-piloto-3-nichos-9-videos-20261109.json`)

## O que permanece no AutoEditorVideo

- Automação e agendamento de produção, scripts de upload, autorizações e logs.
- Tokens, credenciais OAuth, nomes de Secrets e conexões autenticadas.
- Manifestos de lotes massivos (incluindo o lote Otaku Multicena com 50 vídeos), cuja migração exigiria revisão de compatibilidade.
- Imagens, áudio, MP4 e demais artefatos; nenhuma mídia foi presumida como existente.
- As configurações e o histórico do repositório original **não foram alterados**.

## Riscos e decisões

- Identificar canal por nome não autoriza upload. Configurações novas estão com `conectado=false`, `upload_habilitado=false`, `privacidade=private`.
- Nomes de marca propostos não foram aplicados ao YouTube; o nome observado está explícito no `canal.json`.
- Os modelos `imagem-estatica` e `camadas-animadas` são **provisórios** e ainda não têm IA/renderizador conectados.
- Arquivos editoriais mantêm caminhos e estados legados; podem conter roteiros obsoletos e **não** são diretamente aceitos pelo pipeline de vídeo.
- No caso infantil, `feito_para_criancas=true` é obrigatório para o canal correspondente.
- Os vídeos não devem ser publicados em massa nem repetidos sem revisão editorial e verificação de duplicatas.

## Próximas etapas

1. Validar identidades, políticas e opções de modelo de cada canal.
2. Converter individualmente material editorial em `canal/<id>/videos/<video-id>/video.json`.
3. Criar etapas reais de geração/renderização e verificar MP4 em modo de teste.
4. Configurar OAuth independente por canal, com checagem de identidade e primeiro upload privado.
5. Somente depois configurar agendamento/publicação com controle de custos e qualidade.
