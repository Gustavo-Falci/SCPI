"""Emissão e revogação dos tokens de serviço da câmera (um por sala).

Uso:
    python scripts/camera_token.py emitir --sala "Sala 101" [--descricao "PC da bancada"]
    python scripts/camera_token.py listar
    python scripts/camera_token.py revogar --id 3

Deliberadamente fora da API: emitir segredo por HTTP exigiria rate-limit,
auditoria e cuidado extra com o token plano em log e DOM. Instalar câmera já é
tarefa de quem tem SSH na VM.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from infra.database import DB_INDISPONIVEL, get_db_cursor
from infra.migrations import ensure_camera_tokens_table
from repositories.camera_tokens import emitir_token, listar_tokens, revogar_token


def _erro(mensagem: str):
    """Sai com mensagem em stderr e código 1 — nunca com sucesso silencioso."""
    print(f"erro: {mensagem}", file=sys.stderr)
    sys.exit(1)


def _preparar():
    """Confirma o banco e garante a tabela, nesta ordem.

    A checagem explícita existe porque `ensure_camera_tokens_table()` chama
    `cur.execute` sem testar o cursor: com o pool sem conexão ela estoura
    `AttributeError: 'NoneType' object has no attribute 'execute'`, que não diz
    a um operador que o problema é o banco estar fora.
    """
    with get_db_cursor() as cur:
        if not cur:
            _erro(
                "banco indisponível (verifique DB_HOST/DB_PORT no .env e se o "
                "Postgres está no ar). Nenhuma alteração foi feita."
            )
    ensure_camera_tokens_table()


def _emitir(args):
    _preparar()
    token = emitir_token(args.sala, args.descricao)
    print(f"Sala:  {args.sala}")
    print(f"Token: {token}")
    print()
    print("Guarde agora — o banco só tem o hash, este valor não é recuperável.")
    print("Configure no .env da câmera: CAMERA_SERVICE_TOKEN=<token acima>")


def _listar(_args):
    _preparar()
    linhas = listar_tokens()
    if linhas is DB_INDISPONIVEL:
        _erro("banco indisponível — a lista abaixo seria falsa, então não vai nenhuma.")
    if not linhas:
        print("Nenhum token emitido.")
        return
    print(f"{'ID':>4}  {'SALA':<24} {'CRIADO':<20} {'ÚLTIMO USO':<20} SITUAÇÃO")
    for t in linhas:
        situacao = f"revogado em {t['revogado_em']:%Y-%m-%d}" if t["revogado_em"] else "ativo"
        ultimo = f"{t['ultimo_uso_em']:%Y-%m-%d %H:%M}" if t["ultimo_uso_em"] else "nunca"
        print(f"{t['id']:>4}  {t['sala']:<24} {t['criado_em']:%Y-%m-%d %H:%M}     {ultimo:<20} {situacao}")


def _revogar(args):
    resultado = revogar_token(args.id)
    if resultado is DB_INDISPONIVEL:
        # Não pode virar "não encontrado ou já revogado": quem revoga token
        # comprometido leria isso como missão cumprida.
        _erro(f"banco indisponível — o token {args.id} NÃO foi revogado. Tente de novo.")
    if resultado:
        print(f"Token {args.id} revogado.")
    else:
        print(f"Token {args.id} não encontrado ou já revogado.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Tokens de serviço da câmera")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_emitir = sub.add_parser("emitir", help="emite um token para uma sala")
    p_emitir.add_argument("--sala", required=True)
    p_emitir.add_argument("--descricao", default=None)
    p_emitir.set_defaults(func=_emitir)

    sub.add_parser("listar", help="lista tokens (sem mostrar o segredo)").set_defaults(func=_listar)

    p_revogar = sub.add_parser("revogar", help="revoga um token pelo id")
    p_revogar.add_argument("--id", type=int, required=True)
    p_revogar.set_defaults(func=_revogar)

    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise  # _erro() e o argparse já disseram o que precisava
    except Exception as e:
        # Banco fora derruba `ensure_camera_tokens_table()` e `emitir_token()`
        # com exceção. Traceback cru de psycopg2 num script de operação não
        # ajuda ninguém a decidir o que fazer; a mensagem, sim.
        _erro(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
