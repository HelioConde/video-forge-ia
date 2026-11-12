# Modelos de produção

Cada diretório em `modelos/` representa **um modelo reutilizável de produção de vídeo**. Um modelo determina como as etapas do vídeo serão produzidas: roteiro, imagem, animação, voz e renderização.

```text
modelos/
├── camadas-animadas/modelo.json
└── imagem-estatica/modelo.json
```

Os modelos são independentes dos canais. Um canal referencia `modelo_padrao`, e cada vídeo pode sobrescrevê-lo com `modelo`.

## Modelo de produção x modelo de IA

**Modelo de produção**: receita (ex.: `camadas-animadas`, `imagem-estatica`) que descreve as etapas.

**Modelo de IA**: serviço/identificador utilizado por cada etapa (ex.: campos `provedor` e `modelo_ia` dentro de `etapas`). Esses campos estão nulos até a escolha/configuração dos provedores. A arquitetura permite que cada etapa tenha um provedor e modelo de IA próprio.

Nesta fase, os arquivos são **declarações de configuração**, não implementações de geração de mídia.

## Precedência

`video.json.modelo` (quando definido) > `canal.json.modelo_padrao`.

Não há herança implícita entre modelos de produção. Para criar outra receita, adicione `modelos/<id>/modelo.json` com `id` igual ao nome da pasta e escolha esse ID no canal/vídeo.

Credenciais e tokens nunca devem ser salvos nos modelos.

## Geradores especializados (nova camada)

O modelo técnico (`modelos/`) descreve COMO transformar a cena em mídia:
imagem estática, camadas, renderização etc. O **gerador especializado**
(`geradores/<id>/gerador.json`) descreve QUE FLUXO editorial e audiovisual
deve ser seguido: por exemplo anime, infantil, dorama ou qualquer novo
nicho cadastrado. São conceitos independentes e combináveis.

Um canal pode definir `gerador_padrao`, e cada vídeo pode usar `gerador`.
O catálogo é aberto: não existe uma lista fixa de nichos no Python.
Confira [geradores/README.md](../geradores/README.md). Por enquanto
os geradores são planos, não executores reais de IA.

