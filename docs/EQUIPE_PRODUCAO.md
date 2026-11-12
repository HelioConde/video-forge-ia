# VideoForge AI — estrutura de produtora e delegação

## Gerente e equipe

O proprietário é o **gerente geral humano**. Envia uma demanda por vídeo/canal e aprova decisões críticas. O **diretor** distribui trabalhos a líderes dos departamentos Editorial, Criação, Audiovisual e Qualidade/Distribuição. Cada líder possui uma lista de especialistas lógicos, que só se tornam executores quando forem ligados a conectores autorizados.

O arquivo `agentes/equipe.json` mantém as oito funções visuais atuais para preservar os postos do escritório, e passa a ter `manager` e `departamentos` para uma equipe escalável. Os especialistas não substituem os agentes do Canvas, nem são apresentados como IA online. É proibido anunciar progresso de geração sem um executor real e evidência de saída.

## Exemplo de demanda

Um pedido do gerente inclui canal, tema, público, duração e modo de publicação. O motor `videoforge/production/dispatcher.py` produz o **grafo de subtarefas**:

- Pesquisa/briefing → roteiro.
- Com roteiro pronto: **título, descrição, tags, thumbnail, storyboard e narração** podem ser delegados a especialistas diferentes.
- Storyboard → imagens → animação; roteiro → legendas; edição depende de animação, áudio e legendas.
- QA depende de edição, capa e metadados.
- Aprovação gerencial depende de QA; envio só pode ser habilitado por autorização de publicação fora do planejador.

## Estados e evidências

`blocked` = faltam dependências; `ready` = pode começar; `in_progress` = execução conectada demonstrável; `done` = resultado verificado; `failed` = bloqueio. Um artefato de saída deve existir antes de concluir um trabalho, não basta um texto do agente dizendo 'pronto'. Uma revisão negativa reabre exclusivamente os componentes dependentes. Publicação e despesas pagas só acontecem por workflows com limites e aprovação.

O `dispatcher.py` do estágio atual **não executa IAs, renderiza vídeo ou faz upload**: sua primeira entrega é um planejamento determinístico verificável e testável, para permitir a adição posterior de executores por especialidade.

## Integração com animações do escritório

A hierarquia também define quem conversa com quem, que sala usar e como visualizá-lo. O sistema de eventos do backend será a origem de estados reais; o Canvas poderá representar reuniões/entregas com sprites novos quando existirem, mantendo demonstrativos visuais separados. Novos agentes visuais serão adicionados por expansão de layout, não por duplicar avatars e inventar tarefas.

## Abrir uma demanda no GitHub

No workflow `VideoForge - Receber demanda do gerente` (`.github/workflows/production-request.yml`), o proprietário informa ID, canal, tema e duração. O Actions valida a demanda e gera `demanda.json` e `plano.json` como artefatos, com 18 entregas delegadas e dependências. **Este workflow não chama IA nem publica vídeos**. No futuro, cada especialidade terá um executor que só trabalhará com credenciais próprias e limites de orçamento.

## Mudança de direção: um gerente editorial para cada canal

A direção artística/produção mantém seus 18 especialistas, mas não escolhe
pautas para todos os canais de modo uniforme. São cinco agentes gerentes,
um por canal, com autonomia de pesquisa, hipóteses editoriais e delegação
isolada. Para o Otaku Multicena: inventário de todos os vídeos do canal
+ Analytics em janelas comparáveis → detecção de temas já usados →
ranking de duração/gênero/anime → proposta de pauta inédita →
roteiro → narração, título, descrição, tags, arte, edição e QA.
A decisão é acompanhada de evidências e pode ser recusada por falta de
amostras. `docs/GERENTES-CANAIS.md` detalha o piloto e os bloqueios.
A integração real de IA e o upload permanecem desabilitados nesta entrega.

## Subgerente — reconhecimento e evolução do time

A equipe recebe **um novo agente independente chamado Subgerente**,
responsável por verificar avaliações de QA, atribuir pontos transparentes
(0–100 por entrega), apresentar rankings por especialidade e encaminhar
planos individuais de melhoria ao gerente geral. Ele é o **nono agente
visual** e fica em pé na área colaborativa, reutilizando animações locais.

A pontuação usa média das entregas aprovadas, nunca soma de vídeos ou
métricas de YouTube. Um membro com menos de três trabalhos de QA possui
nota indisponível, não zero. Resumos sem artefatos verificáveis e
autoavaliações são bloqueados. Os funcionários não devem ajustar suas
próprias notas. O sistema não executa ações de IA automaticamente.
Ver `docs/SUBGERENTE.md`.
