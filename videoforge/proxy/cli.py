"""Painel CLI backend. Catalogo offline ou diagnostico SOMENTE leitura."""
from __future__ import annotations
import argparse
import json
import sys
import os
from .client import ProxyClient, ProxyError
from .quota_diagnostic import summarize_quota


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Codex Proxy para VideoForge AI (backend)")
    parser.add_argument("--action", choices=("catalog", "probe", "quota"), default="catalog")
    parser.add_argument("--usage-mode", choices=("cached", "live"), default="cached")
    args = parser.parse_args(argv)
    if args.action == "catalog":
        print(json.dumps({
            "schema": "videoforge/proxy-capabilities/v1",
            "backend_only": True,
            "active_connection": False,
            "endpoints": ProxyClient.capabilities(),
        }, indent=2, ensure_ascii=False))
        return 0
    if args.action == "quota" and args.usage_mode == "live":
        if (os.getenv("PROXY_QUOTA_LIVE_APPROVED") != "yes"
                or os.getenv("GITHUB_EVENT_NAME") != "workflow_dispatch"
                or os.getenv("GITHUB_REPOSITORY") != "HelioConde/video-forge-ia"
                or os.getenv("GITHUB_REF") != "refs/heads/main"
                or os.getenv("GITHUB_RUN_ATTEMPT") != "1"):
            print("QUOTA_LIVE_NOT_AUTHORIZED", file=sys.stderr)
            return 1
    try:
        proxy = ProxyClient(timeout=8)
        if args.action == "quota":
            report = summarize_quota(proxy, usage_mode=args.usage_mode)
            print(json.dumps(report, ensure_ascii=False))
            return 0
        live = proxy.health_live()
        if not isinstance(live, dict) or live.get("status") != "ok":
            raise ProxyError("Health check inesperado")
        health = proxy.health()
        models = proxy.models()
        accounts = proxy.accounts()
        rows = accounts.get("accounts", []) if isinstance(accounts, dict) else []
        model_list = models.get("data", []) if isinstance(models, dict) else []
        print(json.dumps({
            "schema": "videoforge/proxy-private-preflight/v1",
            "state": "read_only_connected",
            "server_live": True, "authenticated": True,
            "account_records": len(rows),
            "eligible_accounts": sum(1 for x in rows if isinstance(x, dict)
                                     and x.get("eligible_now") is True),
            "model_catalog_entries": len(model_list),
            "rotation_strategy": health.get("rotation") if isinstance(health, dict) else None,
            "calls_generated": 0, "images_generated": 0,
            "videos_uploaded": 0,
        }, ensure_ascii=False))
        return 0
    except (ProxyError, ValueError):
        # Nao propagar mensagens nem dados de OAuth de servidores externos.
        print(json.dumps({"schema":"videoforge/proxy-private-preflight/v1",
                          "state":"unavailable", "calls_generated":0,
                          "videos_uploaded":0}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
