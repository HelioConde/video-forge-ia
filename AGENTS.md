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

O escritório em `site/` deve ser organizado e consumir apenas snapshots públicos saneados gerados por `scripts/build_dashboard_data.py`. O navegador não roda agentes nem recebe tokens. Nunca exibir execução simulada como se fosse real; não copiar informações privadas para o Pages. Publicação permanece manual até revisão de visibilidade. Consulte `docs/ESCRITORIO_AGENTES.md`.

**Cadastro de funcionários:** manter funções, dependências e identificação em `agentes/equipe.json`, sem duplicar a equipe em vários módulos. O painel deve consumi-lo por meio do exportador, nunca por leitura de arquivos privados no navegador.
