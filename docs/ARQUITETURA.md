# Arquitetura proposta — VideoForge AI

## Organização por canal e por modelo

```text
canal/
  <canal-id>/
    canal.json
    videos/
      <video-id>/
        video.json
modelos/
  <modelo-id>/
    modelo.json
videoforge/
  config.py     # resolve a receita do canal/vídeo
  pipeline.py   # prepara e valida storyboard (dry-run)
tests/
.github/workflows/
output/         # gerados localmente, fora do Git
```

- **Canal**: define idioma, configurações de publicação e `modelo_padrao`.
- **Vídeo**: guarda duração, roteiro/cenas e `modelo` opcional. Quando existe, substitui o modelo padrão do canal.
- **Modelo de produção**: receita independente do canal para etapas de roteiro, imagem, animação, voz e montagem.
- **Modelo de IA**: provedor e identificação configuráveis para cada etapa (`provedor` e `modelo_ia`), ainda não integrados.

## Padrão obrigatório de organização e manutenção contínua

**Regra permanente: toda implementação, manutenção, correção, experimento ou refatoração deve deixar o projeto organizado.** Nenhuma funcionalidade deve ser considerada concluída se introduzir desordem estrutural, duplicação desnecessária ou documentação desatualizada.

### Responsabilidades por local

| Caminho | Responsabilidade |
| --- | --- |
| `canal/<id>/canal.json` | Configurações próprias do canal e modelo padrão |
| `canal/<id>/videos/<id>/video.json` | Definição de cada vídeo e seleção opcional de modelo |
| `modelos/<id>/modelo.json` | Receitas reutilizáveis de produção e opções de IA |
| `videoforge/` | Código reutilizável de orquestração, configuração e módulos de produção |
| `tests/` | Testes correspondentes aos comportamentos implementados |
| `.github/workflows/` | Pipelines de CI e agendamento, sem lógica de negócio duplicada |
| `docs/` | Documentação de arquitetura, decisões e procedimentos |
| `output/` | Saídas geradas, logs e mídias locais; conteúdo não versionado |

### Checklist obrigatório para cada mudança

1. **Antes:** inspecionar os diretórios e os módulos afetados; aproveitar os componentes existentes antes de criar outros.
2. **Durante:** colocar cada arquivo na pasta de sua responsabilidade, manter nomes claros, funções coesas e interfaces estáveis.
3. **Isolamento:** não misturar configurações, assets nem credenciais entre canais; herança de modelo por vídeo precisa continuar funcionando.
4. **Limpeza:** evitar arquivos descartáveis ou duplicados; só apagar conteúdo após confirmar que não é utilizado.
5. **Depois:** atualizar README/documentação e exemplos quando houver mudança de comportamento, executar testes e inspecionar a estrutura final.
6. **Integração:** manter os workflows organizados e validar que automações novas não substituam ou quebrem as existentes.

As regras também estão resumidas no [README principal](../README.md) e devem ser seguidas por agentes conforme [AGENTS.md](../AGENTS.md).

## Catálogo de canais herdado do AutoEditorVideo

| Pasta | Chave legada | Modelo inicial |
| --- | --- | --- |
| `canal/otaku-br/` | `br` | `camadas-animadas` |
| `canal/otaku-en/` | `en` | `imagem-estatica` |
| `canal/gamer/` | `games` | `imagem-estatica` |
| `canal/manu-kids/` | `kids` | `camadas-animadas` |
| `canal/alchemy-lab/` | `alchemy` | `imagem-estatica` |

Os padrões são provisórios. Os arquivos em `arquivo-editorial/` são referências e não scripts de publicação. O teste de 10 segundos agora fica em `canal/alchemy-lab/videos/teste-10s/`.

Consulte [MIGRACAO_AUTOEDITORVIDEO.md](MIGRACAO_AUTOEDITORVIDEO.md). Nenhum token ou upload foi migrado.

## Meta

Automatizar: pauta > roteiro > planejamento de cenas > geração de imagens e camadas > animação > narração > montagem > validação > upload no YouTube.

## Módulos planejados

1. **Content Planner**: tema, canal, vídeo, roteiro, storyboard e continuidade dos personagens.
2. **Scene Composer**: imagem completa de referência; extração de cenário, personagens e objetos transparentes.
3. **Animator**: anima os elementos separadamente, preservando enquadramento e identidade.
4. **Audio Studio**: vozes e efeitos licenciados, com sincronização.
5. **Renderer**: renderização FFmpeg com legendas e áudio.
6. **Quality Gate**: duração, consistência, assets ausentes e duplicatas.
7. **YouTube Publisher**: OAuth/YouTube Data API, teste privado antes de liberar publicação.
8. **Scheduler / Observability**: GitHub Actions, logs, recuperações e status de cada canal.

## Etapas de entrega

- [x] Organização de pastas por canal, vídeo e modelo reutilizável.
- [x] Herança de modelo do canal com sobrescrita por vídeo, com testes.
- [x] Storyboard JSON de exemplo e validação no GitHub Actions.
- [ ] Integração real de IA para roteiros, imagens, animação e voz.
- [ ] Renderização de um MP4 de 10 segundos.
- [ ] Upload privado de teste no YouTube.
- [ ] Agendamento automático e monitoramento.

## Segurança e limites atuais

- O protótipo **não gera imagens, áudio ou MP4 e não realiza uploads**.
- Credenciais devem ficar em Actions Secrets, nunca em `canal/` ou `modelos/`.
- Testar em privado primeiro, impedir uploads repetidos, validar qualidade e controlar custo das APIs.

## Estrutura do escritório Pixel Studio

O frontend estático é organizado em `site/`:

- `office-art.js`: desenho original do estúdio e dos personagens, com dados de posição reutilizados pela interação.
- `office-renderer.js`: engine Canvas 2D, câmera, zoom, gestos de toque, hit-testing e minimapa.
- `app.js`: seleção, detalhes dos agentes/canais e consumo seguro do snapshot de status.
- `styles.css` e `index.html`: disposição responsiva, HUD e painéis.
- `data/status.json`: snapshot público gerado pelo backend, sem credenciais.

Os arquivos de arte não executam serviços de IA. A publicação da interface ocorre por GitHub Pages Actions e é independente da publicação de vídeos no YouTube.

## Integração opcional PixelLab

- `personagens/<slug>/profile.json`: descrição e animações próprias de cada personagem.
- `videoforge/pixellab/client.py`: autenticação, APIs PixelLab v2, jobs e exportações.
- `videoforge/pixellab/cli.py`: seleção da base existente ou criação, animações e planejamento seguro.
- `.github/workflows/pixellab-character.yml`: comando manual com controle de custos e divulgação.
- `tests/test_pixellab.py`: testes simulados sem rede.
- `output/pixellab/`: arquivos temporários fora do Git.

A geração de sprites ainda não está conectada ao Canvas nem ao renderizador dos vídeos. Veja `docs/PIXELLAB.md`.

## Orquestração PixelLab em lote para Work

- `videoforge/pixellab/batch.py`: consulta GET a base exata, compara movimentos/direções, reutiliza grupo anterior por ID, limita novas gerações e escreve relatório público sem UUID.
- `.github/workflows/pixellab-work.yml`: workflow manual para o ChatGPT Work, com modos planejar/gerar, autorização de custo/exposição, trava `pixellab-personagens` e máximo de oito POSTs por disparo.
- `tests/test_pixellab_batch.py`: simulações sem API paga, cobrindo reuso, antduplicação, bloqueios e exportações.
- `docs/PIXELLAB-WORK.md`: operação, parâmetros e procedimento de retomada segura.

A fonte de verdade dos movimentos continua sendo a conta PixelLab; o GitHub armazena apenas relatório de execução e ZIPs opcionais por sete dias, nunca segredos ou mídias geradas permanentemente no Git.
