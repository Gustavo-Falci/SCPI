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

from infra.migrations import ensure_camera_tokens_table
from repositories.camera_tokens import emitir_token, listar_tokens, revogar_token


def _emitir(args):
    ensure_camera_tokens_table()
    token = emitir_token(args.sala, args.descricao)
    print(f"Sala:  {args.sala}")
    print(f"Token: {token}")
    print()
    print("Guarde agora — o banco só tem o hash, este valor não é recuperável.")
    print("Configure no .env da câmera: CAMERA_SERVICE_TOKEN=<token acima>")


def _listar(_args):
    ensure_camera_tokens_table()
    linhas = listar_tokens()
    if not linhas:
        print("Nenhum token emitido.")
        return
    print(f"{'ID':>4}  {'SALA':<24} {'CRIADO':<20} {'ÚLTIMO USO':<20} SITUAÇÃO")
    for t in linhas:
        situacao = f"revogado em {t['revogado_em']:%Y-%m-%d}" if t["revogado_em"] else "ativo"
        ultimo = f"{t['ultimo_uso_em']:%Y-%m-%d %H:%M}" if t["ultimo_uso_em"] else "nunca"
        print(f"{t['id']:>4}  {t['sala']:<24} {t['criado_em']:%Y-%m-%d %H:%M}     {ultimo:<20} {situacao}")


def _revogar(args):
    if revogar_token(args.id):
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
    args.func(args)


if __name__ == "__main__":
    main()
