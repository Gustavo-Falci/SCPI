"""Relógio UTC do sistema.

Substitui `datetime.utcnow()`, deprecado desde o Python 3.12 e marcado para
remoção. Devolve datetime **aware**, fixado em UTC.

Era naive até 2026-08-03, porque `RefreshTokens.expires_at` e
`PasswordResetCodes.expires_at` eram `TIMESTAMP` sem time zone e psycopg2 as
lia de volta naive — comparar naive com aware levanta `TypeError`. Essas
colunas viraram `TIMESTAMPTZ` (`ensure_timestamptz_tokens`, em
infra/migrations.py), então a comparação agora funciona dos dois lados e o
valor deixa de depender do TimeZone da sessão do banco.

Ao gravar em coluna nova, use `TIMESTAMPTZ`. Uma coluna `TIMESTAMP` recebendo
um datetime aware descarta o offset silenciosamente, e o valor passa a
significar hora de parede — que é exatamente o bug que esta migração fechou.
"""
from datetime import datetime, timezone


def agora_utc() -> datetime:
    """Instante atual em UTC, com tzinfo."""
    return datetime.now(timezone.utc)
