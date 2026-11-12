# Geradores de vídeo — catálogo aberto

O VideoForge AI **não tem lista fixa de nichos**. Cada pasta `geradores/<id>/gerador.json` representa um gerador especializado com seu próprio processo. É possível acrescentar documentário, terror, educação, culinária, notícias, games, storytelling, animação 3D e outros sem alterar o registrador.

Os primeiros perfis (anime, kids, dorama) são **contratos planejados**, não executores de IA ativos. O catálogo apenas descobre e valida fluxos. Ele não gera imagens, não monta vídeos e não publica.

## Estrutura

- `geradores/<id>/gerador.json`: nome, perfil editorial e etapas específicas.
- `videoforge/generators/registry.py`: catálogo genérico que descobre novas pastas automaticamente.
- `videoforge/config.py`: prioridade de escolha `video.json.gerador` > `canal.json.gerador_padrao`, ambos opcionais.
- `modelos/<id>/modelo.json`: modelo técnico independente (ex.: imagens estáticas ou camadas animadas).
- `videoforge/production/`: executores reais, mídia, QA, orçamento e aprovação, quando efetivamente conectados.

## Como adicionar um novo gerador

1. Crie `geradores/documentario/gerador.json` copiando um exemplo e trocando `id`, `nome`, `descricao` e `perfil`.
2. Defina uma lista `pipeline` de etapas com identificadores únicos, `operation`, `agent`, `after` e `output`. Operações e nomes de geradores **não têm enumeração fixa**: crie as etapas necessárias para o novo formato.
3. Todas as dependências devem existir e não podem formar ciclos. O estágio `image-generation` exige `source: integrated-image-generator`; qualquer estágio `render` deve depender das gerações de imagens, e o `quality-review` deve depender dos renders.
4. Mantenha `execution_enabled: false`, `auto_publish_enabled: false` e `requires_human_approval: true`. Cadastro de perfil não concede execução ou autorização para gastos.
5. Configure `"gerador_padrao": "documentario"` no canal, ou `"gerador": "documentario"` apenas em um vídeo. Sem configuração, o fluxo legado permanece inalterado.
6. Execute `python -m unittest discover -s tests -p 'test_generator_registry.py' -v` e depois a suíte geral.

**Adicionar uma pasta válida basta para descobrir o perfil** com `list_generators()`. Para realmente produzir imagens, animações e MP4 daquele tipo, ainda será necessário implementar e testar os respectivos executores privados. O arquivo JSON nunca carrega código arbitrário.

## Regras compartilhadas que cada gerador deve respeitar

- Imagens narrativas exclusivamente do gerador de imagens integrado ao programa, nunca do assistente ou de desenhos programáticos; falhas interrompem a produção, conforme `config/production-image-policy.json`.
- Evidências de saída reais antes de declarar uma etapa concluída; nada de simular trabalhadores ativos.
- QA técnico/editorial independente e aprovação humana antes de publicar.
- Autorização explícita e limites de recursos antes de chamadas pagas.
- Credenciais somente no backend protegido, jamais em `geradores/` ou GitHub Pages.

## Perfis iniciais de exemplo

- **Anime:** pesquisa e roteiro, cenas ilustradas, narração, montagem e revisão.
- **Kids:** segurança infantil, continuidade de personagens, camadas animadas, voz, legendas e QA infantil.
- **Dorama:** bíblia de personagens, continuidade, cenas, diálogos, movimentos e revisão.

Um mesmo canal pode escolher um gerador diferente por vídeo ou série. As regras editoriais e os módulos de produção são independentes da infraestrutura e dos modelos técnicos já existentes.
