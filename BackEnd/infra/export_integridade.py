"""Cálculo e verificação de integridade para exports LGPD."""
import datetime
import hashlib
import hmac
import json
import zoneinfo


def _payload_canonico(dados: dict) -> bytes:
    """Serializa JSON com chaves ordenadas e sem espaços extras (forma canônica)."""
    return json.dumps(
        dados, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def calcular_integridade(dados: dict, hmac_key: str) -> dict:
    """Retorna manifesto com SHA-256 + HMAC-SHA256 do payload canônico."""
    payload = _payload_canonico(dados)
    sha = hashlib.sha256(payload).hexdigest()
    mac = hmac.new(hmac_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return {
        "sha256": sha,
        "hmac_sha256": mac,
        "algoritmo": "HMAC-SHA256",
        "versao_schema": "1.0",
        "gerado_em": datetime.datetime.now(
            tz=zoneinfo.ZoneInfo("America/Sao_Paulo")
        ).isoformat(),
    }


def verificar_integridade(dados: dict, manifesto: dict, hmac_key: str) -> bool:
    """Verifica se o manifesto corresponde aos dados sob a mesma chave HMAC."""
    payload = _payload_canonico(dados)
    sha_esperado = hashlib.sha256(payload).hexdigest()
    mac_esperado = hmac.new(
        hmac_key.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(
        sha_esperado, manifesto.get("sha256", "")
    ) and hmac.compare_digest(mac_esperado, manifesto.get("hmac_sha256", ""))
