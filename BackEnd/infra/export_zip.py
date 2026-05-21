"""Montagem do ZIP multi-formato para o export LGPD."""
import io
import json
import zipfile


_LEIA_ME = """RELATÓRIO DE DADOS PESSOAIS — SCPI
====================================

Este pacote contém todos os seus dados pessoais armazenados pelo Sistema de
Controle de Presença Inteligente (SCPI), em atendimento à Lei Geral de Proteção
de Dados Pessoais — LGPD (Lei 13.709/2018), Art. 18 §1, inciso I.

Arquivos incluídos:
-------------------
  - dados.pdf          : Relatório legível em PDF.
  - dados.json         : Dados estruturados em JSON (interoperável).
  - foto-perfil.jpg    : Foto de cadastro biométrico, se houver.
  - INTEGRIDADE.txt    : Hash SHA-256 e assinatura HMAC do conteúdo.
  - LEIA-ME.txt        : Este documento.

Verificação de integridade:
---------------------------
O arquivo INTEGRIDADE.txt contém:
  - SHA-256 do JSON canônico (verificável por qualquer pessoa).
  - HMAC-SHA256 com chave do servidor SCPI (verificável apenas pela equipe).

Para validar o HMAC, encaminhe o ZIP intacto ao DPO/contato técnico do SCPI.

Direitos do titular (LGPD Art. 18):
-----------------------------------
  I    - confirmação da existência de tratamento;
  II   - acesso aos dados;
  III  - correção de dados incompletos ou inexatos;
  IV   - anonimização, bloqueio ou eliminação;
  V    - portabilidade dos dados;
  VI   - eliminação dos dados pessoais;
  VII  - informação sobre compartilhamento;
  VIII - informação sobre não fornecimento de consentimento;
  IX   - revogação do consentimento.

Para exercer qualquer direito, contate o responsável pelo sistema.
"""


def _formatar_integridade(manifesto: dict) -> str:
    return (
        "MANIFESTO DE INTEGRIDADE — Export LGPD SCPI\n"
        "============================================\n\n"
        f"Algoritmo       : {manifesto['algoritmo']}\n"
        f"Versão schema   : {manifesto['versao_schema']}\n"
        f"Gerado em       : {manifesto['gerado_em']}\n\n"
        f"SHA-256         : {manifesto['sha256']}\n"
        f"HMAC-SHA256     : {manifesto['hmac_sha256']}\n\n"
        "O SHA-256 é calculado sobre o JSON canônico (chaves ordenadas,\n"
        "sem espaços, UTF-8). Para recomputar:\n"
        "  python -c \"import json,hashlib; "
        "print(hashlib.sha256(json.dumps(json.load(open('dados.json')),"
        "sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())\"\n\n"
        "O HMAC só pode ser verificado pelo servidor SCPI (chave secreta).\n"
    )


def montar_zip_export(
    dados: dict,
    pdf_bytes: bytes,
    manifesto: dict,
    foto_bytes: bytes | None = None,
) -> bytes:
    """Monta ZIP contendo PDF, JSON, foto opcional, manifesto de integridade e LEIA-ME."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "dados.json", json.dumps(dados, ensure_ascii=False, indent=2)
        )
        z.writestr("dados.pdf", pdf_bytes)
        z.writestr("INTEGRIDADE.txt", _formatar_integridade(manifesto))
        z.writestr("LEIA-ME.txt", _LEIA_ME)
        if foto_bytes:
            z.writestr("foto-perfil.jpg", foto_bytes)
    return buffer.getvalue()
