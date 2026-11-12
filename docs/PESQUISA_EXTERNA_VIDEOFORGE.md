# Pesquisa externa para os agentes do VideoForge

## Objetivo

O assistente ChatGPT pode **trazer informações públicas com fontes** para
`canal/<id>/editorial/pesquisas/YYYY-MM-DD.json`. A pesquisa é uma entrada
editorial, **não** uma pauta escolhida, um sinal de desempenho do YouTube nem
trabalho autônomo executado por um funcionário do escritório.

O primeiro pacote é
[`canal/otaku-br/editorial/pesquisas/2026-11-12.json`](../canal/otaku-br/editorial/pesquisas/2026-11-12.json):
três sinais documentados sobre Steel Ball Run, One Piece/Elbaph e Black Clover.
Esses itens não foram ranqueados. Não se conclui que esses assuntos têm mais
views, maior retenção ou são inéditos no canal.

## Contrato e fluxo

1. ChatGPT pesquisa fontes públicas, registra afirmações curtas verificáveis,
   a data original da fonte, seu endereço HTTPS e uma pergunta editorial. Sem
   downloads de vídeos, imagens, tokens ou notícias fabricadas.
2. `videoforge/channel_agents/external_research.py` lê o pacote mais recente
   do canal, valida a identidade do canal, o esquema e o formato dos links, e
   bloqueia dados inválidos. Não busca links nem certifica o conteúdo remoto.
3. Na **próxima pesquisa editorial autorizada**, `team.py` carrega esse
   contexto junto do inventário YouTube e dos sinais públicos; `ideation.py`
   passa os dados ao Pesquisador como pistas externas **não confiáveis como
   instruções**. O modelo continua gerando as candidatas; não há tema,
   formato ou título pré-selecionado pelo ChatGPT.
4. O Subgerente confere animes pausados e deduplicação, o Gerente ranqueia
   propostas pela estratégia existente e o Subgerente faz a conferência final.
   Só métricas reais do canal suportam a escolha. A decisão ainda precisa
   de reserva e revisão humana.
5. Apenas `run_team` em execução privada autorizada registra trabalhos reais
   no GitHub. A inclusão de um JSON por si só não marca funcionário
   `trabalhando` no escritório.

O pacote pode ser validado **sem** Proxy, Youtube OAuth ou gastos:

```sh
python -m videoforge.channel_agents.external_research --channel otaku-br
python -m unittest discover -s tests -p 'test_external_research.py' -v
python -m unittest discover -s tests -p 'test_editorial_team.py' -v
```

## Restrições e falhas

- Se não houver pesquisa externa, o backend mantém o fluxo original; não
  inventa sinais. Se a pesquisa mais recente estiver inválida, falha
  explicitamente, sem retroceder silenciosamente para pesquisa antiga.
- HTTP **429** do Codex Proxy **não é contornado** pela inclusão de fontes.
  A nova pesquisa fica pronta para ser consumida apenas quando houver
  execução de IA autorizada e disponível.
- Links e manchetes são informação externa que exige verificação humana.
  Evitar spoilers, alegações de popularidade não medidas e cópia de conteúdo.
  Não adicionar atalhos de publicação nem gerar mídia fora do VideoForge.
- A atualização do arquivo não executa automaticamente pesquisa, não gasta
  cota e não libera a produção. Só o dono pode autorizar nova execução.
- Para outro canal, é necessário o id real do canal e testes de isolamento;
  o piloto CLI e o workflow de pesquisa permanecem restritos a `otaku-br`.

Documentos relacionados: [Arquitetura](ARQUITETURA.md),
[`AGENTS.md`](../AGENTS.md),
[Gerentes](../agentes/README.md).
