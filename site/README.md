# VideoForge AI — Escritório de Agentes

Site estático original em `site/`, com **Canvas 2D em tela inteira**, inspirado no conceito de escritórios pixel-art de agentes, como Pixel Agents para VS Code. O código e os gráficos são próprios, sem copiar ativos visuais de terceiros.

## Executar localmente

```bash
python scripts/build_dashboard_data.py
python -m http.server 8000 --directory site
```

Abra `http://localhost:8000` para visualizar o escritório fullscreen com os oito agentes e os cinco canais. Use mouse/toque para selecionar os personagens, arraste para navegar, use scroll/+/− para zoom e o botão ⛶ para fullscreen.

## Publicação automática do GitHub Pages

1. Em **Settings → Pages → Build and deployment**, configure **Source: GitHub Actions**.
2. Verifique se sua conta GitHub permite publicar Pages de um repositório privado.
3. Revise a visibilidade da página e os dados que ficarão públicos.
4. O workflow **VideoForge AI - Escritorio de Agentes (Pages)** inicia automaticamente a cada alteração relevante na branch `main` (interface, agentes, canais, exportador ou testes).
5. Para republicar sem mudanças, use **Actions → VideoForge AI - Escritorio de Agentes (Pages) → Run workflow**.
6. Após o primeiro deploy bem-sucedido, consulte a URL indicada em **Settings → Pages**.

A publicação é automática em commits relevantes para o painel e também pode ser iniciada manualmente. **O usuário já escolheu GitHub Actions como fonte do Pages.** Como sites Pages podem ser públicos, mantenha somente nomes de canais e funções públicas no snapshot.

## Limitações atuais

GitHub Pages é estático: **não hospeda agentes reais**, não inicia tarefas, não envia vídeos, não instala bibliotecas de orquestração e não conhece automaticamente o que os agentes executam. Cada funcionário aparecerá como **não conectado** até uma execução de backend confiável fornecer seus eventos.

O script `scripts/build_dashboard_data.py` monta dados com os **nomes e modelos** dos canais e sem IDs do YouTube, tokens, segredos ou logs privados. A página tenta atualizar o snapshot a cada minuto, mas isso não é acompanhamento em tempo real: precisa existir um novo deploy para aparecerem novos estados.

## Integração futura do backend

O gerador suporta opcionalmente `--events caminho/relatorio.json` com um JSON controlado, por exemplo:

```json
{
  "agents": [
    {"id": "roteirista", "status": "trabalhando", "canal": "otaku-br", "tarefa": "Planejando um vídeo"}
  ]
}
```

IDs: `diretor`, `roteirista`, `artista`, `animador`, `narrador`, `editor`, `revisor`, `publicador`. Estados aceitos: `nao_conectado`, `aguardando`, `trabalhando`, `revisao`, `concluido`, `erro`.

Esse relatório precisa ser criado por jobs reais e revisado para evitar vazamento de informações, não por simulação de atividade. A execução manual atual **não** incorpora nenhum arquivo de eventos.

**Segurança:** o site GitHub Pages pode ficar público mesmo com código em repositório privado. Nomes públicos dos canais e as funções da equipe podem ser vistos por visitantes. A publicação automática assume que a exposição de nomes públicos de canais e funções da equipe foi autorizada; nunca adicionar dados privados ao exportador.

## Estrutura do frontend

- `index.html`: barra compacta e Canvas ocupando todo o espaço restante, com controles sobrepostos.
- `styles.css`: adapta o HUD, botões e painel flutuante a desktop e celular.
- `office-art.js`: arte Canvas 2D original — cenário, iluminação, mobiliário, objetos de cada profissão e oito personagens diferentes.
- `office-renderer.js`: motor de viewport, zoom/arraste, minimapa, hit-testing e desenho da arte no Canvas.
- `app.js`: busca o snapshot público, atualiza indicadores, gerencia seleção e inspector.
- `data/status.json`: estado mínimo exportado do backend.

Toda a arte é programática e própria. Não importa bibliotecas nem assets do Pixel Agents. Animações de interface não significam execução de trabalho.

## Navegação aperfeiçoada

- **No celular:** o zoom padrão prioriza preencher a altura da janela, eliminando grandes faixas vazias; arraste para visitar outras mesas.
- **Minimapa clicável:** localize uma estação e mova a câmera tocando no mapa no canto inferior direito.
- **Seleção pela lista:** ao tocar em um funcionário, a câmera foca o respectivo posto no celular.
- **Centralização:** use o botão ⌖ para voltar ao enquadramento original.
- **Arte aprimorada:** tapetes, placas de postos, avisos de planejamento e console gráfico de edição são desenhados no próprio Canvas.

## Pixel Studio v3

A versão atual reorganiza o cenário em três ambientes, com piso texturizado, móveis desenhados em Canvas, janelas, plantas, iluminação de teto, salas de criação e edição e personagens com roupas e ferramentas próprias.

O minimapa fica **recolhido no celular** para não encobrir os trabalhadores. Toque em "Minimapa" para expandi-lo. O status dos agentes continua baseado exclusivamente no snapshot gerado pelo backend, sem simulação de tarefas executadas.

A arquitetura visual separa **arte** (`office-art.js`) de **interação** (`office-renderer.js`). Qualquer nova personalização deve respeitar essa divisão e a regra permanente de organização do repositório.

## Cenários PixelLab incorporados ao Canvas

As imagens **originais aprovadas** estão versionadas em `site/assets/pixellab/`: três salas 256×256 px e seis objetos transparentes 64×64 ou 96×96 px. O arquivo `manifest.json` registra dimensões e SHA-256 de cada imagem. Foi produzido a partir dos artifacts das execuções PixelLab 42844340885 e 42845029772.

O botão **▦ / ✦** na barra de ferramentas alterna entre a arte original e a composição PixelLab. O modo PixelLab é habilitado automaticamente após carregar os nove PNGs; se qualquer arquivo falhar, o escritório antigo continua funcionando. O Canvas desenha as três salas sem distorção, posiciona os seis objetos sem fundo e mantém oito agentes selecionáveis. O minimapa e o foco de agentes usam os mesmos slots da arte ativa.

Os agentes ainda são desenhados pela arte original de `office-art.js` (sem spritesheet de personagem ligado); o estágio atual conecta **cenários e objetos**, não as 48 animações de personagens. O código não chama a API PixelLab no navegador, não transmite tokens e não altera o status real dos agentes. A interface do escritório continua sendo uma projeção de dados do backend.

## Sprites animados Alex — integração v4

O PixelLab exportou `character-frames.zip` com seis movimentos (`idle`, `walk`, `type`, `sit`, `talk`, `wave`) e oito direções. Cada combinação possui quatro frames de **88×88** pixels (área útil 64×64 com margem transparente). A action `pixellab-import-alex.yml` valida a identidade da exportação e monta os seis atlas PNG em `assets/pixellab/agents/alex/`. Cada atlas tem **352×704**: quatro colunas de frames e oito linhas de direções. O manifesto controla ordem, dimensões e hashes sem IDs privados.

O novo `agent-animator.js` carrega os seis atlas em paralelo, valida dimensões e oferece desenho síncrono, sem `await` dentro do Canvas. `office-art.js` escolhe a animação conforme o status **real** do agente; sem eventos de backend o agente fica em `idle`. O botão de prévia no painel de agentes percorre os seis movimentos sem alterar o status registrado. Para conforto, `prefers-reduced-motion` usa o primeiro frame.

Se faltar algum atlas, a aplicação mantém os oito personagens desenhados originalmente e o restante do escritório continua funcionando. **Por enquanto os oito postos reutilizam a aparência Alex**; personagens distintos podem ser cadastrados depois. O navegador não chama a API PixelLab nem usa credenciais.
