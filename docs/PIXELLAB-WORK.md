# Animações PixelLab em lote pelo ChatGPT Work

O Work pode disparar o workflow **PixelLab - Animacoes em lote para Work**,
usando [GitHub Actions](https://github.com/HelioConde/video-forte-ia/actions/workflows/pixellab-work.yml)
ou o GitHub CLI. Não precisa abrir uma execução para cada direção.

## Configuração única

- Acesso GitHub autorizado no Work.
- Secret `PIXELLAB_API_TOKEN` existente (verificado em 10/11/2026).
- Secret `PIXELLAB_CHARACTER_ID` com o UUID **do personagem correto já criado**.
  A conta tinha 27 personagens na última auditoria: não escolher um aleatoriamente.
- Repositório é **público**, então os artefatos ZIP exportados podem ser públicos.
  Marcar a autorização de custos e visibilidade pública antes de gerar.

O usuário não precisa informar o token ao ChatGPT. O GitHub Actions injeta os
Secrets somente durante a execução.

## Primeiro disparo: planejamento gratuito

No Work: abrir o GitHub Actions, escolher o workflow `pixellab-work.yml`
e disparar com `modo=planejar`, `movimento=todos`, `max_novas=4`,
`liberar_grupos_desconhecidos=false`.

O resultado será apresentado no resumo e no `report.json` do artifact.
Ele informa direções já existentes, as faltantes e as que entrariam no próximo lote.
Nenhum POST de geração é usado.

Se houver grupos com nomes desconhecidos, o script para de maneira segura,
para evitar duplicação. Para liberar, verificar os grupos na biblioteca
PixelLab e só então usar `liberar_grupos_desconhecidos=true`.

## Gerar as próximas animações

Depois da revisão, disparar `modo=gerar`, `movimento=todos`,
`max_novas=4`, `confirmar_custo=true` e `artefatos_publicos=true`.
`exportar_zips=true` é opcional: os ZIPs podem incluir IDs privados.
Se não for necessário baixar o spritesheet, deixar falso.

O lote só executa a primeira leva de no máximo 4 combinações ausentes.
Novas execuções consultam novamente o PixelLab e pulam direções já salvas.
Uma execução permite no máximo **8** novas chamadas pagas.
O preço por chamada depende do modelo/plano; esse limite não é um teto monetário.

Para continuar, o Work pode repetir o workflow após verificar o relatório da
rodada anterior, até `missing_directions` chegar a zero. Não lançar várias
execuções simultaneamente. O grupo de concorrência
`pixellab-personagens` é compartilhado com a ação individual.

A API permite `animation_group_id` para acrescentar direções a um grupo
existente. O script reutiliza o ID e não recria o personagem base.
Se houver mais de um grupo com o mesmo movimento ou um grupo sem ID válido,
a execução para antes de cobrar.

## Comandos pelo GitHub CLI (dentro do Work)

Planejar:

~~~bash
gh workflow run pixellab-work.yml --repo HelioConde/video-forte-ia --ref main -f modo=planejar -f movimento=todos -f max_novas=4
~~~

Gerar até quatro novas direções, depois de verificar o plano:

~~~bash
gh workflow run pixellab-work.yml --repo HelioConde/video-forte-ia --ref main -f modo=gerar -f movimento=todos -f max_novas=4 -f confirmar_custo=true -f artefatos_publicos=true
~~~

Comando local de inspeção (em checkout autorizado, com os dois secrets no ambiente):

~~~bash
python -m videoforge.pixellab.batch --mode plan --scope all --max-new 4
~~~

## O que o Work deve verificar após cada rodada

- Status do workflow e do job no GitHub.
- Total de direções criadas/concluídas no relatório.
- Se houve erro ou timeout, **não repetir o POST** sem consultar jobs no PixelLab.
- Conclusão do plano seguinte: se faltam mais direções, repetir somente
  dentro dos limites/autorizações do usuário.

## Salvamento e privacidade

Os sprites gerados ficam persistidos na própria biblioteca do PixelLab.
O GitHub Actions salva `output/pixellab-batch/report.json` como artifact.
A exportação opcional também gera `character-frames.zip` e `spritesheet.zip`
no artifact por 7 dias; não faz commit de PNGs no repositório público.
Não enviar tokens, UUIDs, prompts pessoais ou URLs de mídia nos resumos públicos.

O fluxo **não** edita o site do escritório nem publica vídeos no YouTube.

Referência: https://api.pixellab.ai/v2/docs

## Instrução pronta para o ChatGPT Work

O usuário pode passar esta tarefa ao Work:

> Abra o repositório HelioConde/video-forte-ia. Siga AGENTS.md e docs/PIXELLAB-WORK.md.
> Primeiro confira o Secret PIXELLAB_CHARACTER_ID e o personagem base correto
> (ID já fornecido na conversa), usando a interface do GitHub em modo Work.
> Nunca divulgue token nem UUID nos logs, código ou comentários públicos.
> Inicie o workflow pixellab-work.yml em modo planejar. Leia o relatório e
> confirme quais das 48 combinações de seis movimentos e oito direções
> existem. Somente então, com a autorização de custo já dada pelo usuário e
> mantendo o limite de até oito POSTs pagos por rodada, execute o workflow
> em modo gerar para produzir direções realmente faltantes.
> Aguarde cada rodada terminar e revalide o inventário antes da próxima.
> Em erros, 409 ou timeout, pare e investigue, sem repetir cobranças cegamente.
> Por padrão não exporte ZIPs públicos. Se precisar baixar spritesheets,
> habilite exportar_zips apenas após confirmar a exposição pública.
> Não recrie o personagem original, não altere poses existentes e não publique no YouTube.
> Informe quantas animações já existiam, quantas foram criadas e o link de cada Action.
> Para poses/estados (sitting, typing, thinking, waving), use o workflow individual
> pixellab-character.yml somente após checar se já existem na conta.
