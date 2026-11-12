# Subgerente — avaliação e evolução contínua dos agentes

## Missão

O **Subgerente** é o **nono agente visual** da produtora VideoForge AI.
Ele presta contas ao gerente geral humano, monitora a qualidade das
entregas dos funcionários de IA e fornece **ranking de pontos,
feedback construtivo e sugestões de melhorias concretas**.

Não adicionamos outro departamento: o Subgerente supervisiona as oito
funções visuais, 27 especialidades lógicas e cinco gerentes de canais.
**Não avalia a si próprio nem o gerente humano.**

## Como funciona o ranking

Pontuação **de 0 a 100 por entrega**, desde que haja evidência comprovada
por revisão independente. Uma avaliação exige um identificador de tarefa
único, canal, período, hash do artefato entregue, aprovação de QA e
`reviewer_id` diferente do funcionário avaliado.

| Critério | Pontos máximos | Motivo |
| --- | ---: | --- |
| Qualidade verificada pelo QA | 50 | Recompensa rigor, clareza, originalidade e precisão |
| Consistência da entrega | 15 | Entrega aprovada sem várias correções |
| Colaboração validada | 10 | Contexto e apoio útil a outros trabalhadores |
| Evolução verificada | 20 | Mudança de qualidade demonstrada em novo artefato |
| Conformidade e segurança | 5 | Respeito a direitos, políticas e regras |
| **Total** | **100** | Média por entrega, não soma de tarefas |

Revisões são permitidas: uma entrega aprovada após duas tentativas ainda
recebe pontos; aprendizado validado pode compensar uma primeira tentativa
mais fraca. O Subgerente **nunca pontua** tarefas recusadas, arquivos sem
hash, formulários sem evidência, ou autoavaliações.

### Regras antimanipulação

- **Mínimo de 3 trabalhos aprovados** na mesma janela para entrar no
  ranking. Menos que isso = `amostra_insuficiente`, pontos `null`,
  não 0 e não "pior funcionário".
- Uma tarefa só pode pontuar **uma vez**. O algoritmo bloqueia IDs de
  job duplicados e usa **média**, evitando que 40 vídeos ruins vençam
  3 vídeos bons.
- A revisão de qualidade precisa vir de um dos papéis QA independentes;
  o Subgerente não pode definir `quality=100` por conta própria.
- O bônus de evolução de 20 pontos exige hash de um artefato anterior,
  resumo da melhoria e aprovação de um revisor independente. Apenas
  alegar "aprendi" não gera pontos.
- Os funcionários têm funções e dificuldades diferentes. Há classificação
  geral ilustrativa **e posição no grupo profissional**: `visual`,
  `especialistas` ou `gerentes`. Comparações entre tarefas de
  dificuldade diferente precisam de contexto humano.
- Visualizações, CTR ou inscritos do YouTube são indicadores do canal,
  **não critérios diretos de recompensa individual**: dependem de
  fatores fora do controle de um roteirista, artista ou QA.

### Feedback individual

O sistema sugere mudanças específicas e verificáveis, como:
melhorar checklist de QA, reduzir erros recorrentes, documentar
contexto entre agentes e testar uma melhoria concreta. Os conselhos
são **propostas**. O Subgerente não modifica arquivos, prompts ou
modelos automaticamente, não dá punições, não libera gastos e não
publica vídeos. Melhorias em código precisam passar por testes,
revisão e autorização do gerente humano.

## Integração

- Cadastro: `agentes/equipe.json` (agente `subgerente`, modelo nulo e
  `habilitado: false` até integração real).
- Pontos e feedback: `videoforge/production/subgerente.py`.
- Testes sem IA: `tests/test_subgerente.py`.
- Interface: nona estação em pé na área colaborativa
  (`site/office-map.js`); animações existentes do PixelLab são reutilizadas
  sem gerar imagens pagas; selecionar **Subgerente** na aba Funcionários
  apresenta o ranking e próximos pontos de melhoria.
- O arquivo público `site/data/status.json` informa somente resultados
  agregados, nunca tokens ou registros de QA com identificadores de
  vídeos e hashes. Enquanto não houver tarefas verificadas, a interface
  mostra `Aguardando evidências` em vez de inventar pontuação.
- O exportador aceita `--performance-evidence <arquivo-privado.json>`
  **somente em backend confiável**, usando
  `videoforge/performance-evidence/v1`. Essa entrada **não autentica
  sozinha** a fonte: uma integração produtiva deve verificar de fato os
  artefatos/hashes e a identidade do revisor via armazenamento privado
  e fluxo de QA antes de fornecê-la ao calculador. Não aceitar entrada
  enviada pelo navegador.

## Próximas etapas para operação real

1. Conectar a fila de produção a artefatos reais e avaliações QA.
2. Verificar hashes/assinaturas e a identidade de QA no backend.
3. Persistir os registros e pontuações com trilha de auditoria e
   separação por canal sem expor informações privadas.
4. Produzir feedback semanal para cada agente, acompanhar se melhorias
   propostas foram adotadas e verificar qualidade antes/depois.
5. Exibir posição, evolução e desempenho real apenas quando houver
   dados suficientes — e sem incentivar manipulação de métricas.

O objetivo é **desenvolver uma equipe que melhore a qualidade do conteúdo
e ajude os canais a crescer**, não criar uma competição de quantidade.
