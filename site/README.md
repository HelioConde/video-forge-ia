# VideoForge AI — Escritório de Agentes

Site estático original em `site/`, inspirado no conceito de escritórios pixel-art de agentes, como Pixel Agents e Pixel Office. O código e os gráficos são próprios, sem copiar ativos visuais de terceiros.

## Executar localmente

```bash
python scripts/build_dashboard_data.py
python -m http.server 8000 --directory site
```

Abra `http://localhost:8000` para visualizar os oito agentes e cinco canais.

## Publicação manual do GitHub Pages

1. Em **Settings → Pages → Build and deployment**, configure **Source: GitHub Actions**.
2. Verifique se sua conta GitHub permite publicar Pages de um repositório privado.
3. Revise a visibilidade da página e os dados que ficarão públicos.
4. Execute **Actions → VideoForge AI - Escritorio de Agentes (Pages) → Run workflow**.
5. Depois do deploy, consulte a URL indicada em **Settings → Pages**.

A publicação está **deliberadamente limitada a `workflow_dispatch`**. Não ocorre automaticamente ao fazer push, evitando expor informação de um repositório privado sem revisão.

## Limitações atuais

GitHub Pages é estático: **não hospeda agentes reais**, não inicia tarefas, não envia vídeos, não instala bibliotecas de orquestração e não conhece automaticamente o que os agentes executam. Cada funcionário aparecerá como **não conectado** até uma execução de backend confiável fornecer seus eventos.

O script `scripts/build_dashboard_data.py` monta dados com os **nomes e modelos** dos canais e sem IDs do YouTube, tokens, segredos ou logs privados. A página tenta atualizar o snapshot a cada minuto, mas isso não é acompanhamento em tempo real: precisa existir um novo deploy para aparecerem novos estados.

## Integração futura do backend

O gerador suporta opcionalmente `--events caminho/relatorio.json` com um JSON controlado, por exemplo:

```json
{
  "agents": [
    {"id": "roteirista", "status": "trabalhando", "canal": "otaku-br", "tarefa": "Planejando um vídeo"}
  ]
}
```

IDs: `diretor`, `roteirista`, `artista`, `animador`, `narrador`, `editor`, `revisor`, `publicador`. Estados aceitos: `nao_conectado`, `aguardando`, `trabalhando`, `revisao`, `concluido`, `erro`.

Esse relatório precisa ser criado por jobs reais e revisado para evitar vazamento de informações, não por simulação de atividade. A execução manual atual **não** incorpora nenhum arquivo de eventos.

**Segurança:** o site GitHub Pages pode ficar público mesmo com código em repositório privado. Nomes públicos dos canais e as funções da equipe podem ser vistos por visitantes. Não publique até estar confortável com essa exposição.
