# VideoForge — monitoramento de saúde a cada 30 minutos

**Objetivo:** identificar falhas reais de workflows e inconsistências na
configuração do escritório sem gastar tokens do Codex Proxy, créditos PixelLab,
cota do YouTube ou criar vídeos.

## Agendamento

O workflow `.github/workflows/videoforge-healthcheck.yml` executa em
`12,42 * * * *`, ou seja, **duas vezes por hora**, em intervalos de
30 minutos. O GitHub Actions pode atrasar ou eventualmente omitir um cron
sob carga; o agendamento não garante início exato no minuto marcado.

- `pull_request`: somente testes offline, sem autorização de recursos privados.
- `push` na `main` de alterações do próprio monitor: testes e auditoria
  pública de leitura, permitindo verificar a implantação.
- `schedule`: auditoria pública e local somente leitura.
- `workflow_dispatch`: permite verificar o próprio monitor manualmente,
  **sem disparar outros workflows**, sem iniciar inferência e sem utilizar
  Environment Secrets.

## O que verifica

1. Consulta os últimos runs de evento **push na main** dos workflows
   `validate.yml`, `pages.yml`, `channel-manager-analysis.yml`,
   `codex-proxy-backend.yml` e `external-research-validation.yml`.
   Verifica a situação mais recente, sem recuperar logs ou dados de runs
   manuais privados. Os dois primeiros são considerados obrigatórios.
2. Confere, offline, o snapshot local do escritório: **9 agentes**,
   incluindo Subgerente, e **5 canais/gerentes**. Isso não é prova
   de execução autônoma.
3. Registra um resumo com links de Actions. Falha de CI, timeout,
   ação necessária, startup failure ou execução travada por mais de 90 min
   deixam o job em erro, para facilitar investigação. Estados em andamento
   e cancelados não são tratados como falhas conclusivas.

A automação horária do ChatGPT **“VideoForge — corrigir problemas”** é
separada: pode investigar as falhas e propor/aplicar correções autorizadas
usando o repositório, PRs e testes. O monitor não se autoedita, não reinicia
jobs, não abre issues repetidas, não altera Secrets e não tenta contornar
HTTP 429.

**Limites:** sucesso em CI não prova que a conta de IA pode gerar texto,
que os agentes estejam conectados ou que um vídeo foi criado/publicado.
Uma falha de `workflow_dispatch` privado também não é automaticamente
classificada como CI de `push`, pois pode depender de aprovação ou cota.
É preciso investigar separadamente o diagnóstico de uso do Proxy.

## Segurança

O job tem permissões restritas `contents: read` e `actions: read`,
usa somente `GITHUB_TOKEN` efêmero do workflow e acessa metadados públicos
da API GitHub. Não usa `PROXY_ACCOUNTS_JSON`, OAuth, tokens YouTube,
`VIDEOFORGE_DRAFT_ENCRYPTION_KEY_B64`, PixelLab ou artefatos privados.
Não envia notificações externas. No relatório aparecem apenas nome de
workflow, estado e ID/URL pública do run.

## Verificação

Testes offline:
```bash
python -m unittest discover -s tests -p 'test_health_monitor.py' -v
```

Execução manual opcional:
```powershell
gh workflow run videoforge-healthcheck.yml -R HelioConde/video-forge-ia --ref main
```

A implantação deve ser confirmada pelo **run automático de push na main**
ou por um `workflow_dispatch` comprovadamente disparado. Nunca alegar
que o cron executou antes de haver um run `schedule` verificável.
