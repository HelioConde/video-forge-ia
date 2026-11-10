# VideoForge AI — plano de animações sociais e interação com o escritório

## Resultado da auditoria — 10/11/2026

O workflow `pixellab-social-audit.yml` consultou somente a API PixelLab e confirmou **6 grupos** no Alex: `idle`, `walk`, `type`, `sit`, `talk`, `wave`. Nenhum dos movimentos sociais pesquisados foi encontrado. O frontend já reutiliza **48 combinações (6×8 direções)** e quatro quadros por combinação.

Ações de cantar sentado, beber café, beber água, jogar, entrar no banheiro e levantar da cadeira **não são animações existentes**. A demonstração no site usa apenas `walk` e `idle`, com marcadores provisórios e indicação explícita de que as ações específicas estão pendentes.

## Lista priorizada de animações que faltam

| Prioridade | Movimento novo | Aplicação | Dependências de objeto |
|---|---|---|---|
| P0 | `stand_up` | Levantar da cadeira ao sair da mesa | cadeira em camada separada |
| P0 | `sit_down` | Transição de caminhada para sentado | cadeira e âncora |
| P0 | `sing_seated` | Cantar sentado no estúdio, com microfone; não é apenas `talk` | microfone, suporte, fones |
| P0 | `sip_coffee` | Beber café com caneca na mão, levantar e pousar caneca | caneca, mesa, máquina de café |
| P0 | `drink_water` | Pegar copo e beber água em pé | bebedouro, copo |
| P0 | `play_gamepad` | Jogar sentado segurando controle | sofá/cadeira, videogame, tela |
| P0 | `open_door` | Abrir/fechar porta de salas e do banheiro | porta com estados aberta/fechada |
| P1 | `wash_hands` | Lavar as mãos ao sair do banheiro | pia, torneira |
| P1 | `put_on_headphones` | Colocar/tirar fones e ajustar microfone | fone, microfone |
| P1 | `stretch` | Alongar, espreguiçar e relaxar em intervalos | espaço livre |
| P1 | `read_script` | Ler roteiro antes da gravação | folha/tablet |
| P1 | `laugh` / `clap` | Socializar e reagir a atividades | nenhum |
| P1 | `arcade_play` | Jogar em máquina arcade | gabinete arcade |
| P1 | `cheer` | Celebrar ao ganhar um jogo ou terminar uma tarefa | nenhum |
| P2 | `draw_tablet` | Desenhar e revisar ilustração | mesa digitalizadora |
| P2 | `edit_timeline` | Editar vídeo no monitor | monitor, mouse |
| P2 | `inspect_storyboard` | Conferir cenas, apontar para quadro | mural |
| P2 | `use_phone` | Consultar celular no intervalo | telefone |
| P2 | `carry_cup` | Andar segurando copo ou caneca | caneca/copo |

### Prioridade por direção e orçamento

A geração deve usar **somente as direções necessárias para cada contexto**, verificando cada grupo na biblioteca antes de cobrar. `walk` e `idle` já têm oito direções; não repetir.

- `stand_up`, `sit_down`: começar com sul e norte (mesas) e validar transições.
- `sing_seated`, `sip_coffee`, `play_gamepad`: começar com **sul** ou **norte**, conforme orientação do móvel.
- `drink_water`, `open_door`, `wash_hands`: começar com **norte**, porque o personagem encara o objeto fixo.
- `stretch`, `read_script`, `laugh`, `clap`: pelo menos sul; outras direções quando exigidas pelo enquadramento.
- Só ampliar para oito direções depois de aprovar os sprites, o encaixe com móveis e os custos por chamada.

**Não há teto monetário conhecido:** consultar os custos da API/conta antes de cada novo lote pago. Nenhuma nova geração paga foi autorizada por este plano isoladamente.

## Cenários e objetos necessários

1. **Copa/café:** balcão, cafeteira, canecas, mesas, bandejas; pontos de pegar e guardar objetos.
2. **Bebedouro:** dispenser, copos, pia e lixeira, com animação de encher copo.
3. **Salão de jogos:** sala independente em pixel art, entrada e saída, sofá, videogame, dois controles, máquinas arcade, mesa de jogos opcional.
4. **Banheiro:** porta externa e sinalização, lavatório/pia. O personagem **entra pela porta e sai após pausa**; não é necessário e nem recomendável mostrar ação íntima.
5. **Estúdio de áudio:** microfone, pedestal, fones, cadeira com âncoras para mãos/cabeça e animação `sing_seated`.
6. **Objetos interativos:** caneca, copo, joystick, porta com duas aparências, cadeiras e máquina de café separadas do fundo.

As salas atuais do PixelLab são escritório principal, sala criativa e laboratório de mídia. Marcadores para jogos/WC no site são provisórios, não salas completas.

## Contrato de interação (próximas etapas)

- Cada sala expõe `walkable`/colisores, zonas de entrada, portas e pontos de interação com coordenadas e direção de aproximação.
- O agente recebe uma meta `walk_to(target)`, planeja rota com A* ou grafo de waypoints, movimenta-se em oito direções com animação `walk`, desacelera e troca para `idle`/ação final.
- Áreas com mais de um agente precisam de ocupação ou reservas para evitar sobreposição; personagens devem respeitar ordem de profundidade no Canvas.
- Cadeira/microfone/mesa têm âncoras distintas para mãos, pés e altura do sprite; usar transformação/sobreposição por camada sem deslocar o fundo.
- Executar sequência `sit -> sing_seated -> stand_up` somente com as animações realmente geradas.
- Café: `stand_up -> walk -> pick_up_cup -> sip_coffee -> put_down_cup -> walk -> sit_down`.
- Água: `walk -> fill_cup -> drink_water -> put_down_cup -> walk`.
- Jogos: `walk -> sit_down -> play_gamepad -> stand_up -> walk`.
- Banheiro: `walk -> open_door -> ocultar atrás da porta -> sair -> wash_hands -> walk`; sem visualização íntima.
- Interromper ou cancelar demos caso o backend envie um estado real `trabalhando`, `revisao` ou `erro`. A UI não deve alterar o status, nem contabilizar tarefa concluída por causa de animações.
- Intervalos automáticos futuros precisam ser opcionais e identificados **SIMULAÇÃO VISUAL**; só usar eventos reais para afirmar que o agente está trabalhando.
- Testes de responsividade, navegação, sobreposição, uso de frames, ausência de asset e desempenho em celular.

## O que já foi implementado

O módulo `site/agent-routines.js` oferece **rotas manuais demonstrativas** para café, bebedouro, área de jogos, entrada do banheiro e retorno à mesa, usando apenas sprites existentes `walk` e `idle` e orientação em oito direções. O painel usa a mesma posição que o Canvas e o minimapa. O roteiro de pausa completa depende de gerar sprites/ambientes/objetos listados acima.

A implementação **não representa trabalho real, nem permite beber, jogar ou usar o banheiro com sprites inexistentes**.
