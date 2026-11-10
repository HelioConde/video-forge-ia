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

## Situação atual

**Nenhum desses oito agentes executa IA ainda.** Todos estão configurados com `habilitado=false` e `modelo_ia=null`. A lista serve como contrato para desenvolver os executores e alimentar um painel verdadeiro; a interface nunca deve marcar agente como trabalhando sem evento emitido pelo backend.

## Regras

- Não armazenar chaves, OAuth ou prompts confidenciais em arquivos públicos.
- Proibir publicação sem relatório de revisão e autenticação correta do canal.
- Preferir ferramentas isoladas por etapa e reaproveitar implementações entre canais.
- Registrar eventos pequenos e seguros para exportação no GitHub Pages.
- Sempre manter atualizados o README, o arquivo de equipe e os testes.
