# Diagnóstico seguro de HTTP 429 — Codex Proxy

## Por que este diagnóstico existe

O VideoForge conseguiu iniciar o backend do Codex Proxy, restaurar uma
conta OAuth, listar modelos e reconhecer uma conta elegível. Porém a
pesquisa editorial e uma chamada simples de texto retornaram HTTP 429.
`eligible_now` **não significa** que uma geração esteja liberada.

O upstream pinado oferece `GET /admin/accounts/:account_id/usage`:
`?cached=true` retorna apenas a cópia de cotas do estado local;
sem `cached=true`, a rota poderá renovar OAuth e consultar o endpoint
upstream de uso. Nenhum desses modos gera texto, imagem ou vídeo.

## Modos de execução

O workflow `.github/workflows/codex-proxy-backend.yml` possui:

1. `offline`: somente testes sem rede privada e sem segredos.
2. `private-readonly`: preflight protegido e diagnóstico de **cota em
   cache**; não acessa o endpoint upstream de uso.
3. `private-quota-live`: mesma verificação protegida mais **um único**
   GET de uso da primeira conta elegível. Faz consulta externa de leitura,
   poderá atualizar o token OAuth no backend efêmero, mas não chama
   endpoints de geração e não altera contas no Secret do GitHub.

Os modos privados dependem do Environment `proxy-runtime`, da branch
`main`, de evento `workflow_dispatch` e de `run_attempt=1`.
Não há disparos automáticos com segredos em `push` ou `pull_request`;
não reutilizar essas chamadas em loops ou retentativas.

**Para análise manual de uso sem geração:**

```powershell
gh workflow run codex-proxy-backend.yml -R HelioConde/video-forge-ia --ref main -f mode=private-quota-live
```

Esse comando é opcional e requer autorização do proprietário.
O assistente deve disparar diretamente quando tiver ferramenta autorizada
para `workflow_dispatch`; caso contrário, informar a limitação.
Apenas depois de conferir a cota e os termos do provedor faz sentido
pensar numa nova geração, sempre com aprovação e limite de consumo.

## Saída segura

`python -m videoforge.proxy.cli --action quota --usage-mode cached`
não gera conteúdo. `--usage-mode live` exige aprovação de execução
manual da `main` e variável `PROXY_QUOTA_LIVE_APPROVED=yes`.

A saída é um JSON **agregado e limitado a uma conta amostrada**, por
exemplo `status=quota_not_observed`, `restriction_reported`,
`no_eligible_account`, `live_usage_unavailable` ou
`no_restriction_reported`. A categoria de idade do cache mostra apenas
`within_15_minutes`, `within_24_hours`, `older_than_24_hours` ou
`unknown`.

Nunca imprimir: IDs da conta, endereço de e-mail, tipo de assinatura,
refresh/access token, saldo, porcentagens exatas, resposta do provedor,
conteúdo do prompt, endereços privados ou timestamp exato de renovação.
Não publicar essas informações no GitHub Pages nem armazená-las em artifacts.

**Limite epistemológico:** o diagnóstico de cota pode identificar
uma restrição informada pela API, mas NÃO prova a causa específica
de um HTTP 429 observado anteriormente. Ausência de restrição
reportada também não prova que uma geração terá sucesso.

Testes offline:

```powershell
python -m unittest discover -s tests -p 'test_proxy_quota.py' -v
python -m unittest discover -s tests -p 'test_proxy_client.py' -v
```
