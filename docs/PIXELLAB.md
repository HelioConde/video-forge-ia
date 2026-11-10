# PixelLab — personagens automáticos

O VideoForge AI agora tem um comando GitHub Actions em `.github/workflows/pixellab-character.yml` com um perfil em `personagens/alex/profile.json`.

## Configuração (uma única vez)

1. Entre em https://www.pixellab.ai/account e copie seu token de API.
2. No GitHub, abra **Settings → Secrets and variables → Actions → New repository secret**.
3. Crie o Secret **PIXELLAB_API_TOKEN** com o token. Não coloque o token no chat ou no código.
4. Opcional: salve **PIXELLAB_CHARACTER_ID** como outro Secret contendo o UUID do personagem base que você já criou. Se a conta tiver apenas um personagem, ou um único com nome igual a Alex, o script poderá encontrá-lo automaticamente.

A foto da tela não contém o ID nem o arquivo PNG original do personagem. A API permite consultar seu catálogo após receber o token.

## Executar

Abra **Actions → PixelLab - Gerar personagem e animacoes → Run workflow**. Selecione:

| Operação | Resultado |
|---|---|
| `plan` | Prévia do plano, grátis |
| `create` | Cria personagem com 8 direções |
| `animate` | Anima o personagem existente |
| `state` | Cria uma nova pose/estado de uma base existente, preservando a paleta |
| `ensure-and-animate` | Reusa a base existente; caso a conta não tenha personagens, cria uma base e anima |
| `create-and-animate` | Cria personagem novo e depois anima |
| `export` | Exporta arquivos do personagem sem nova geração |

Movimentos disponíveis: **idle, walk, type, sit, talk, wave**. Para `state`, escolha `estado` entre **sitting, typing, thinking, waving**. O PixelLab aplica a alteração de pose às direções do personagem base. O primeiro teste usa 64×64, animação v3 com quatro frames por direção.

## Custos e privacidade

**O repositório está público.** Os artefatos de execução poderão ser acessíveis por terceiros. Os ZIPs podem incluir o ID do personagem, que permite acessar seus sprites.

Por isso, toda execução real exige marcar **confirmar_custo** e **artefatos_publicos**. Caso contrário, apenas o planejamento grátis é executado. Não há cron automático nem geração em push. Cada execução usa no máximo um POST de criação e um POST de animação; chamadas pagas não são repetidas automaticamente.

Os preços são variáveis e a integração não garante teto monetário; consulte créditos na conta PixelLab. Não produza assets confidenciais nesse repositório público.

## Download dos sprites

Abra a execução no GitHub Actions e baixe o artefato `pixellab-alex-<run_id>`, disponível por sete dias. Ele pode conter:

- `manifest.json`: IDs dos jobs e status da operação;
- `character-frames.zip`: sprites e frames por direção;
- `spritesheet.zip`: spritesheet PNG e layout JSON.

O conteúdo é salvo temporariamente em `output/pixellab/`, que está ignorada pelo Git. Os sprites ainda não foram incorporados ao Canvas e o comando não envia vídeos ao YouTube.

## Testes e comando local

```bash
python -m unittest discover -s tests -p test_pixellab.py -v
python -m videoforge.pixellab.cli --operation plan --character alex --motion walk --direction south
```

Depois de configurar as credenciais como variáveis de ambiente, uma geração autorizada pode ser executada com:

```bash
python -m videoforge.pixellab.cli --execute --operation ensure-and-animate --character alex --motion walk --direction south
```

Para disparar via GitHub CLI:

```bash
gh workflow run pixellab-character.yml --ref main -f operacao=ensure-and-animate -f personagem=alex -f movimento=walk -f direcao=south -f confirmar_custo=true -f artefatos_publicos=true
```

Em caso de timeout, consulte o job anterior no PixelLab antes de reenviar, pois ele pode continuar em execução.

Referência: [API oficial PixelLab v2](https://api.pixellab.ai/v2/docs).

### Exemplo — criar pose sentado (sem recriar personagem)

Configure primeiro o token e, se necessário, o ID base em GitHub Secrets; no Actions selecione `operacao=state` e `estado=sitting`. A API envia a descrição da pose ao endpoint `POST /v2/create-character-state`, com `use_color_palette_from_reference=true` para tentar preservar as cores. Uma nova versão do personagem é exportada para ZIP. A fidelidade visual deve ser revisada antes de usar no escritório.
