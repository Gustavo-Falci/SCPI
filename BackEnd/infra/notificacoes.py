import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger("scpi.notificacoes")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _resend_api_key() -> str:
    return os.getenv("RESEND_API_KEY", "")


def _resend_from() -> str:
    return os.getenv("RESEND_FROM_EMAIL", "SCPI <onboarding@resend.dev>")


def send_expo_push(expo_tokens: list, title: str, body: str, data: dict = None) -> bool:
    valid = [t for t in expo_tokens if t and t.startswith("ExponentPushToken")]
    if not valid:
        logger.debug("Nenhum Expo push token válido para envio.")
        return False

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
            **({"data": data} if data else {}),
        }
        for token in valid
    ]

    payload = json.dumps(messages).encode("utf-8")
    req = urllib.request.Request(
        EXPO_PUSH_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            logger.info("Expo push enviado para %d tokens: %s", len(valid), result)
            return True
    except urllib.error.HTTPError as e:
        logger.error("Expo Push HTTP %s: %s", e.code, e.read().decode("utf-8", errors="replace"))
        return False
    except Exception as e:
        logger.error("Erro ao enviar Expo push: %s", e)
        return False


def send_email_resend(to_email: str, aluno_nome: str, turma_nome: str, hora: str) -> bool:
    api_key = _resend_api_key()
    if not api_key:
        logger.warning("RESEND_API_KEY não configurado — notificação por email ignorada.")
        return False

    html_body = f"""
<html>
<body style="margin:0;padding:0;background:#f0f0f0;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#4B39EF;padding:28px 32px;">
            <h1 style="margin:0;color:#fff;font-size:22px;">SCPI — Presença Confirmada</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 16px;font-size:16px;color:#222;">
              Olá, <strong>{aluno_nome}</strong>!
            </p>
            <p style="margin:0 0 24px;font-size:15px;color:#444;line-height:1.6;">
              Sua presença na disciplina <strong>{turma_nome}</strong> foi
              registrada com sucesso às <strong>{hora}</strong>.
            </p>
            <p style="margin:0;font-size:12px;color:#999;">
              Este é um email automático gerado pelo sistema SCPI.
              Não é necessário responder.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    payload = json.dumps({
        "from": _resend_from(),
        "to": [to_email],
        "subject": f"Presença confirmada em {turma_nome}",
        "html": html_body,
        "text": f"Olá {aluno_nome}, sua presença em {turma_nome} foi registrada às {hora}. — Sistema SCPI",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SCPI/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Email Resend enviado para %s (status %s)", to_email, resp.status)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("Resend HTTP %s: %s", e.code, body)
        return False
    except Exception as e:
        logger.error("Erro ao enviar email via Resend: %s", e)
        return False


def send_email_senha_temporaria(to_email: str, nome: str, senha_temporaria: str, tipo: str) -> bool:
    api_key = _resend_api_key()
    if not api_key:
        logger.warning("RESEND_API_KEY não configurado — envio de credenciais ignorado.")
        return False

    html_body = f"""
<html>
<body style="margin:0;padding:0;background:#f0f0f0;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#4B39EF;padding:28px 32px;">
            <h1 style="margin:0;color:#fff;font-size:22px;">SCPI — Credenciais de Acesso</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 16px;font-size:16px;color:#222;">
              Olá, <strong>{nome}</strong>!
            </p>
            <p style="margin:0 0 24px;font-size:15px;color:#444;line-height:1.6;">
              Você foi cadastrado(a) no sistema SCPI como <strong>{tipo}</strong>.
              Abaixo estão suas credenciais de acesso:
            </p>
            <p style="margin:0 0 8px;font-size:14px;color:#444;">
              <strong>Email:</strong> {to_email}
            </p>
            <p style="margin:0 0 8px;font-size:14px;color:#444;">
              <strong>Senha temporária:</strong>
            </p>
            <div style="background:#f4f4f6;border:1px solid #e2e2e6;border-radius:8px;padding:16px;margin:8px 0 24px;text-align:center;">
              <span style="font-family:Consolas,Monaco,monospace;font-size:20px;font-weight:bold;color:#222;letter-spacing:2px;">{senha_temporaria}</span>
            </div>
            <p style="margin:0 0 24px;font-size:14px;color:#b45309;background:#fef3c7;padding:12px 16px;border-radius:8px;border-left:4px solid #f59e0b;">
              Por segurança, você deverá alterar esta senha no primeiro acesso.
            </p>
            <p style="margin:0;font-size:12px;color:#999;">
              Este é um email automático gerado pelo sistema SCPI.
              Não é necessário responder.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    text_body = (
        f"Olá {nome},\n\n"
        f"Você foi cadastrado(a) no sistema SCPI como {tipo}.\n\n"
        f"Email: {to_email}\n"
        f"Senha temporária: {senha_temporaria}\n\n"
        "Por segurança, você deverá alterar esta senha no primeiro acesso.\n\n"
        "— Sistema SCPI"
    )

    payload = json.dumps({
        "from": _resend_from(),
        "to": [to_email],
        "subject": "Bem-vindo ao SCPI — Suas credenciais de acesso",
        "html": html_body,
        "text": text_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SCPI/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Email de credenciais enviado para %s (status %s)", to_email, resp.status)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("Resend HTTP %s: %s", e.code, body)
        return False
    except Exception as e:
        logger.error("Erro ao enviar email de credenciais via Resend: %s", e)
        return False
