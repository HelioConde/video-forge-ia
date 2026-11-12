# Equipe de agentes — VideoForge AI

Este diretório define os **papéis e responsabilidades** dos agentes que aparecerão no escritório do GitHub Pages.

O arquivo [equipe.json](equipe.json) é a fonte de verdade para os oito funcionários do sistema. Cada um possui um ID estável, uma responsabilidade, suas dependências e o tipo de saída esperada.

## Fluxo planejado

```text
Direção
  └── Roteirista
       ├── Artista visual → Animador ┐
       └── Narrador ─────────────────┤
                                     ▼
                                   Editor
                                     ▼
                                   Revisor
                                     ▼
                                  Publicador
```

O canal ou cada vídeo escolhe um **modelo de produção** em `modelos/<id>/modelo.json`; no futuro, cada etapa poderá escolher seu próprio provedor e modelo de IA. Assim o agente "Roteirista" não precisa obrigatoriamente usar o mesmo modelo do "Artista visual".

## Quem escolhe o tema de cada vídeo?

**A equipe de agentes do canal, não o ChatGPT da conversa.** A pesquisa
editorial funciona por uma divisão verificável:

1. Analista de audiência (módulo de leitura): consulta o histórico completo
   do canal e métricas próprias do YouTube via OAuth somente leitura.
2. Pesquisador (IA pelo Codex Proxy): propõe de quatro a oito hipóteses
   **sem temas pré-selecionados** pelo usuário ou assistente.
3. Subgerente: audita cada proposta contra títulos do histórico completo,
   pautas reservadas e animes pausados (no Otaku Multicena: Death Note).
4. Gerente do canal: escolhe **somente entre ideias aprovadas** usando
   os critérios de desempenho de `videoforge/channel_agents/strategy.py`.
5. Subgerente confere novamente a pauta vencedora. A decisão vira um
   relatório de revisão; **não** produz nem publica o vídeo.

O executor está em `videoforge/channel_agents/team.py`, e a execução
protegida em `.github/workflows/editorial-team-research.yml`.
O escritório recebe evidências reais das etapas pelo GitHub Checks,
distinguindo pesquisa editorial de renderização de mídia.
Os agentes de pesquisa são operações especializadas com IA/ferramentas,
**não nove LLMs permanentemente conectados**. Não atribuir pontuação de
produtividade a funcionários sem seus próprios trabalhos comprovados.

## Situação atual

**Nenhum desses oito agentes executa IA ainda.** Todos estão configurados com `habilitado=false` e `modelo_ia=null`. A lista serve como contrato para desenvolver os executores e alimentar um painel verdadeiro; a interface nunca deve marcar agente como trabalhando sem evento emitido pelo backend.

## Regras

- Não armazenar chaves, OAuth ou prompts confidenciais em arquivos públicos.
- Proibir publicação sem relatório de revisão e autenticação correta do canal.
- Preferir ferramentas isoladas por etapa e reaproveitar implementações entre canais.
- Registrar eventos pequenos e seguros para exportação no GitHub Pages.
- Sempre manter atualizados o README, o arquivo de equipe e os testes.
