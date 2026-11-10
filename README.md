# VideoForge AI

**Gerador modular de vídeos com IA e publicação automatizada no YouTube.**

> **Estado atual: fundação / teste.** O código entregue neste primeiro passo valida um roteiro de cenas (storyboard) e gera um arquivo JSON. **Ainda não gera MP4, não chama provedores de IA e não faz upload.**

## Como vai funcionar

1. Receber tema e configurações de cada canal.
2. Gerar roteiro, diálogos e planejamento das cenas com IA.
3. Criar uma imagem de referência por cena; separar cenário, personagens e objetos com transparência.
4. Animar os elementos mantendo aparência e continuidade.
5. Gerar narração, legendas, música/efeitos e renderizar o vídeo.
6. Validar o resultado e publicar pelo YouTube Data API com OAuth, começando por upload privado.
7. Agendar execuções, registrar resultados e impedir publicações duplicadas.

A arquitetura é detalhada em [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## Primeiro teste (sem custo de IA e sem upload)

Requisito: Python 3.12+.

```bash
python -m unittest discover -s tests -v
python -m videoforge.pipeline --config config/example.json --output output/storyboard.json
```

O comando gera `output/storyboard.json` com duas cenas de 5 segundos (10 segundos no total).
Também existe uma ação manual em **Actions > Validar VideoForge AI > Run workflow**, que executa os testes e disponibiliza o JSON como artifact.

## Estrutura inicial

```text
video-forte-ia/
├── .github/workflows/validate.yml  # CI em modo de teste
├── config/example.json              # storyboard de demonstração
├── docs/ARQUITETURA.md              # módulos e roadmap
├── tests/test_pipeline.py           # verificações automáticas
├── videoforge/pipeline.py           # planejamento e validação
├── videoforge/__init__.py
└── .gitignore
```

## Próximas entregas

- Integração real com provedores de roteiro, imagens e voz.
- Renderização das camadas animadas com FFmpeg.
- Primeira saída MP4 de 10 segundos para avaliação visual.
- Upload privado de teste pelo YouTube; só depois agendamento e publicação automática.

## Proteção de dados

**Não coloque chaves de API, tokens OAuth nem arquivos privados no repositório.**
As credenciais futuras ficarão em GitHub Actions Secrets. A automação deve usar limites de custo, checagem de qualidade e um identificador único para cada publicação.

**Nome do produto:** VideoForge AI. **Nome atual do repositório:** `video-forte-ia` (pode ser renomeado no GitHub).
