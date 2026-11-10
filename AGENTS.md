# AGENTS.md — Regras obrigatórias de manutenção do VideoForge AI

## Princípio permanente

Em **toda tarefa**, preservar e melhorar a organização do repositório. Antes de qualquer edição, leia `README.md` e `docs/ARQUITETURA.md`; mantenha esses documentos alinhados com o código.

## Estrutura por responsabilidade

- `canal/<id>/`: dados e opções de apenas um canal; vídeos em `videos/<id>/`.
- `modelos/<id>/`: modelo de produção independente, reutilizável entre canais ou sobrescrito por vídeo.
- `videoforge/`: código da aplicação modular; não colocar toda a lógica em um só arquivo.
- `tests/`: testes do comportamento alterado.
- `.github/workflows/`: orquestração da CI; não duplicar a lógica de aplicação.
- `docs/`: regras, decisões arquiteturais e documentação.
- `output/`: arquivos e mídia gerados, não versionados.

## Em toda mudança

1. Examinar caminhos e padrões existentes antes de criar algo novo.
2. Separar módulos por função e centralizar funcionalidades reutilizáveis; evitar duplicações e scripts auxiliares desnecessários.
3. Escolher nomes consistentes e manter isoladas as configurações de cada canal e vídeo.
4. Preservar o mecanismo de modelo padrão do canal e substituição opcional no vídeo.
5. Não adicionar segredos, tokens OAuth, mídias geradas ou logs ao Git.
6. Atualizar documentação e exemplos relevantes sempre que alterar contratos, caminhos ou comportamento.
7. Executar testes pertinentes e revisar o diff e a árvore de pastas antes de concluir.
8. Apagar arquivos somente após identificar referências e confirmar que não são mais necessários.
9. Se uma organização diferente for indispensável, documentar antes a razão e o impacto.
10. Não habilitar geração paga ou publicação real sem configuração e autorização explícitas.

**Critério de conclusão:** a tarefa deve funcionar e a aplicação deve continuar organizada, compreensível e sustentável para a próxima modificação.

## Regras adicionais da migração

As pastas de canais reais são `otaku-br`, `otaku-en`, `gamer`, `manu-kids` e `alchemy-lab` dentro de `canal/`. A pasta fictícia `exemplo` foi removida. Não tratar `arquivo-editorial/` ou `conteudos/indice.json` como fila de produção. Não transportar workflows, segredos ou tokens do AutoEditorVideo. Consultar `docs/MIGRACAO_AUTOEDITORVIDEO.md` antes de modificar a migração.

## Regras do dashboard Pages

O escritório em `site/` deve ser organizado e consumir apenas snapshots públicos saneados gerados por `scripts/build_dashboard_data.py`. O navegador não roda agentes nem recebe tokens. Nunca exibir execução simulada como se fosse real; não copiar informações privadas para o Pages. Após a configuração do Pages pelo proprietário, a publicação é automática em mudanças relevantes da branch main e pode ser executada manualmente. O site publicado pode ser público mesmo com repositório privado; exportar apenas dados saneados. Consulte `docs/ESCRITORIO_AGENTES.md`.

**Cadastro de funcionários:** manter funções, dependências e identificação em `agentes/equipe.json`, sem duplicar a equipe em vários módulos. O painel deve consumi-lo por meio do exportador, nunca por leitura de arquivos privados no navegador.

## Política obrigatória de deploy do escritório

Em toda alteração relacionada a `site/`, `agentes/`, `canal/`, `scripts/build_dashboard_data.py` ou testes pertinentes, garantir que o workflow `.github/workflows/pages.yml` valide e publique o Pages automaticamente a partir da branch `main`. Verificar o status do workflow e a URL de deployment antes de comunicar sucesso; se falhar, diagnosticar e corrigir, sem encobrir erros. Não habilitar execução paga de IA ou publicação de vídeos no YouTube por causa do deploy do painel.

## Interface de escritório fullscreen

Em tarefas visuais, manter o desenho original do escritório exclusivamente em `site/office-art.js` e o motor Canvas 2D em `site/office-renderer.js`, com viewport responsivo; manter entrada HTML em `site/index.html`, estilos em `site/styles.css` e integração de dados em `site/app.js`. Manter controles operáveis por mouse/toque e evitar cartões que roubem a maior parte da tela. Não copiar assets proprietários do Pixel Agents; desenhos próprios são obrigatórios. Não inferir trabalho real de animações decorativas. Rodar `node --check` em `site/office-art.js`, `site/office-renderer.js` e `site/app.js` antes do deploy.

## Regra de revisão visual com captura

Para mudanças significativas em Canvas e CSS, renderizar a interface em um navegador, capturar desktop e celular, procurar falhas de proporção, áreas vazias, sobreposição de HUD e usabilidade por toque. Corrigir os problemas encontrados, executar os testes de CI e verificar o Pages após o deploy. Capturas locais são prévias visuais, não evidência automática de publicação em produção.

## Regra de design Pixel Studio

Não voltar a agrupar arte, navegação e integração de dados em um único script. O cenário pertence a `site/office-art.js`; o motor de render e interação pertence a `site/office-renderer.js`; o controlador de UI e snapshot pertence a `site/app.js`. Em celular, o minimapa deve ser recolhível e os elementos flutuantes não podem encobrir a equipe permanentemente. Validar sempre as capturas em desktop e celular após mudar a interface.

## PixelLab

Personagens são definidos em `personagens/<id>/profile.json`, API e CLI em `videoforge/pixellab/` e workflow em `.github/workflows/pixellab-character.yml`. Não inserir tokens ou UUIDs de personagens no código versionado. No repositório público, exigir consentimento de custo e exposição de artefatos. O padrão deve permanecer dry-run, sem cobranças automáticas. Não repetir POST pagos após timeout; consultar jobs anteriores. Ver `docs/PIXELLAB.md`.
