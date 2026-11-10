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
