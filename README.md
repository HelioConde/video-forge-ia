# VideoForge AI

**Gerador modular de vídeos com IA e publicação automatizada no YouTube.**

> **Estado atual: estrutura e testes (dry-run).** Ainda não gera MP4, não chama provedores de IA e não faz upload.

## Organização do projeto

Os cinco canais do AutoEditorVideo estão separados em pastas independentes. Cada canal possui suas próprias regras editoriais e um modelo padrão, que pode ser substituído individualmente em um vídeo.

```text
video-forte-ia/
├── canal/
│   ├── otaku-br/        # Otaku Multicena
│   ├── otaku-en/        # Otaku Reframe
│   ├── gamer/           # Conde Games (marca proposta)
│   ├── manu-kids/       # Emanuelly Kids / Manu Kids
│   └── alchemy-lab/     # Alchemy Lab
│       └── videos/teste-10s/
├── modelos/
│   ├── camadas-animadas/modelo.json
│   └── imagem-estatica/modelo.json
├── videoforge/
├── tests/
├── docs/
└── .github/workflows/
```

Cada canal contém `canal.json`, `conteudos/indice.json`, `README.md` e `videos/`. Referências históricas selecionadas ficam em `arquivo-editorial/` e **não** podem ser usadas como manifestos executáveis.

Confira o [catálogo dos canais](canal/README.md) e o [relatório de migração](docs/MIGRACAO_AUTOEDITORVIDEO.md).

### Como funciona a escolha do modelo

Cada canal tem seu próprio `modelo_padrao` no `canal.json`.
Um vídeo pode optar por `"modelo": "camadas-animadas"` no próprio `video.json`. Sem a propriedade, herda o padrão do canal; as escolhas iniciais são provisórias.

Cada modelo de produção também reserva configurações distintas de **provedor e modelo de IA por etapa** (roteiro, imagem, animação, voz), ainda pendentes de implementação.

Leia [canal/README.md](canal/README.md) e [modelos/README.md](modelos/README.md).

## Regra permanente de organização

**A organização do VideoForge AI é uma exigência contínua, em toda alteração — não apenas na criação do projeto.** Antes de adicionar, alterar, mover ou remover qualquer código, configuração, modelo, vídeo ou automação, é obrigatório preservar uma estrutura clara, consistente e fácil de manter.

- Manter cada canal em `canal/<id>/`, seus vídeos em `canal/<id>/videos/<id>/` e os modelos reutilizáveis em `modelos/<id>/`.
- Separar responsabilidades por módulos; evitar arquivos gigantes, código duplicado e funcionalidades sem relação misturadas no mesmo arquivo.
- Usar nomes descritivos e consistentes para arquivos, pastas, funções e configurações. Não criar scripts ou pastas temporárias sem necessidade.
- Reaproveitar componentes e modelos compartilhados sem comprometer o isolamento dos canais; permitir um modelo próprio por vídeo.
- Manter arquivos gerados, mídias, logs e credenciais fora do código versionado e nos lugares definidos pela arquitetura.
- Ao concluir qualquer alteração, revisar a estrutura, remover apenas artefatos realmente obsoletos com segurança, atualizar a documentação e executar os testes pertinentes.
- Se uma mudança exigir nova pasta ou módulo, justificar sua responsabilidade, respeitar os padrões existentes e atualizar este guia.
- Não reorganizar nem excluir conteúdo de outros canais sem necessidade e sem verificar referências e dependências.

As orientações operacionais para agentes de IA e colaboradores estão em [AGENTS.md](AGENTS.md).

## Escritório virtual de agentes (GitHub Pages)

Foi criado um painel visual com oito funções, cinco canais, filtros e indicadores. Os oito papéis e suas dependências ficam centralizados em [agentes/equipe.json](agentes/equipe.json). Os trabalhadores aparecem como **não conectados** até receberem eventos reais do backend. A publicação usa um workflow **manual** e exige habilitar GitHub Pages nas configurações do repositório.

Veja [site/README.md](site/README.md) e [docs/ESCRITORIO_AGENTES.md](docs/ESCRITORIO_AGENTES.md). **Não confundir a página visual com agentes já executando tarefas.**

## Primeiro teste (sem custo de IA e sem upload)

Requisito: Python 3.12+.

```bash
python -m unittest discover -s tests -v
python -m videoforge.pipeline --video canal/alchemy-lab/videos/teste-10s/video.json --output output/storyboard.json
```

A ação **Actions > Validar VideoForge AI** também roda os testes e salva o storyboard de 10 segundos como artifact. Isso **não** produz um vídeo.

## Próximas entregas

- Gerar roteiro, imagem de referência, personagens/cenários/objetos transparentes e animação por camadas.
- Gerar voz, mixagem e MP4 com FFmpeg.
- Validar o primeiro vídeo de 10 segundos.
- Fazer upload **privado** de teste, depois automatizar o agendamento.

## Segurança

Não adicione chaves de API, tokens OAuth nem mídias privadas no Git. Armazene credenciais em GitHub Actions Secrets; use limites de custo e prevenção contra duplicatas.

**Nome do produto:** VideoForge AI. **Nome atual do repositório:** `video-forte-ia`.
