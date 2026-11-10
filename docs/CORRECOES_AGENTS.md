# Correções do Pixel Studio — agentes e animações

## Resultado

- Os oito agentes têm perfis de movimento em `site/agent-behavior.js`: direção, roteiro, arte, animação, narração, edição, revisão e publicação. O perfil escolhe os movimentos existentes de `agents/alex/production/manifest.json` e usa fallback básico quando ainda falta alguma animação.
- A partir dos **54 movimentos extras importados**, cada profissão reutiliza sprites especializados como `draw_tablet`, `edit_video`, `narrate`, `keyboard_type`, `qa_inspection` e `talk_explain`. Novos sprites podem ser recebidos pelo workflow sem alterar os perfis; movimentos não catalogados nunca são exigidos.
- Quando o backend informa `trabalhando` ou `revisao`, o visual escolhe movimentos do cargo, **sem criar ou modificar atividades reais**. Quando o backend retorna `nao_conectado`, o personagem fica em idle, exceto se a pessoa ativar o botão **🎬 — prévia de profissões**.
- A opção **Conversar com colega** realiza uma simulação de reunião entre dois agents, com caminhada até posições distintas na sala criativa e alternância de `talk_explain` e `listen_focus`. Se o backend informar trabalho ou erro de algum participante, a demonstração é cancelada.
- O botão ☕ mantém os passeios demonstrativos existentes, que não se passam por ações de café/água/jogos/banheiro enquanto não houver animações e objetos reais para cada interação.
- A sala principal PixelLab tem assentos ancorados em `[[218,219],[438,219],[218,322],[438,322],[218,426],[438,426],[218,524],[438,524]]`. Somando o offset de render de 111 pixels, os centros acompanham as cadeiras da imagem original, evitando que os personagens sejam desenhados sobre as janelas. Sprites de 72 px e placas compactas mantêm visível cada fileira.
- O mesmo sprite Alex ainda é reutilizado visualmente para oito funções. Gerar oito aparências individuais exigiria novos assets/decisão do gerente e não é parte desta correção.
- `site/agent-animator.js` busca os sprites novos apenas por GET e não acessa credenciais. Carregamento é sob demanda, especialmente ao ativar a prévia 🎬. Sem sprite carregado, volta ao movimento básico ou ao avatar clássico, sem quebrar a renderização.
- `tests/test_agent_behavior.js`, `tests/test_agent_routines.js` e `tests/test_office_layout.js` validam o catálogo por profissão, a reunião e o posicionamento; `pages.yml` e `validate.yml` testam antes do deployment.

## Limites

A animação visual não comprova que uma IA esteja executando um trabalho. O sistema não cria tarefas, não ativa custos do PixelLab, não publica vídeos nem representa como reais as simulações. O estúdio de jogos e banheiro continua como área planejada, aguardando cenários e interações específicas.
