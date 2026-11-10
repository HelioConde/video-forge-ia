# VideoForge AI

**Gerador modular de vídeos com IA e publicação automatizada no YouTube.**

> **Estado atual: estrutura e testes (dry-run).** Ainda não gera MP4, não chama provedores de IA e não faz upload.

## Organização do projeto

```text
video-forte-ia/
├── canal/                          # uma pasta por canal
│   └── exemplo/
│       ├── canal.json              # modelo padrão do canal
│       └── videos/
│           └── teste-10s/
│               └── video.json      # roteiro e possível modelo próprio
├── modelos/                        # receitas de produção reutilizáveis
│   ├── camadas-animadas/modelo.json
│   └── imagem-estatica/modelo.json
├── videoforge/
│   ├── config.py                    # lê e resolve canal/vídeo/modelo
│   └── pipeline.py                  # valida storyboard JSON
├── tests/
├── docs/ARQUITETURA.md
└── .github/workflows/validate.yml
```

### Como funciona a escolha do modelo

O canal usa `"modelo_padrao": "camadas-animadas"` no `canal.json`.
Um vídeo pode optar por `"modelo": "imagem-estatica"` no próprio `video.json`. Sem a propriedade, herda o padrão do canal.

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

## Primeiro teste (sem custo de IA e sem upload)

Requisito: Python 3.12+.

```bash
python -m unittest discover -s tests -v
python -m videoforge.pipeline --video canal/exemplo/videos/teste-10s/video.json --output output/storyboard.json
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
