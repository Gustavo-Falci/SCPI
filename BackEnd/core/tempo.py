"""Relógio UTC do sistema.

Existe para substituir `datetime.utcnow()`, deprecado desde o Python 3.12 e
marcado para remoção.

O substituto óbvio seria `datetime.now(timezone.utc)`, que devolve datetime
AWARE — e é o que se deve usar em código novo. Aqui não dá: as colunas que
recebem estes valores (`RefreshTokens.expires_at` e `password_reset_tokens.
expires_at`) são `TIMESTAMP` sem time zone, então psycopg2 as devolve naive.
Comparar naive com aware levanta `TypeError: can't compare offset-naive and
offset-aware datetimes` — quebraria o refresh de login e o reset de senha, em
runtime, sem que teste com cursor mockado percebesse.

Daí o `.replace(tzinfo=None)`: o valor é calculado em UTC de verdade (não no
fuso da máquina, como um `datetime.now()` pelado faria) e só então perde o
tzinfo, mantendo exatamente a semântica que `utcnow()` tinha.

Dívida: migrar aquelas colunas para TIMESTAMPTZ e passar o sistema todo para
datetimes aware. Enquanto as tabelas novas (`rate_limit_buckets`,
`login_attempts`, `camera_tokens`) já nascem TIMESTAMPTZ, o schema segue misto.
"""
from datetime import datetime, timezone


def agora_utc() -> datetime:
    """Instante atual em UTC, naive — mesmo contrato do antigo `utcnow()`."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
