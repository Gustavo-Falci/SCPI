import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger("scpi.notificacoes")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM_EMAIL", "SCPI <onboarding@resend.dev>")


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
    if not RESEND_API_KEY:
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
        "from": RESEND_FROM,
        "to": [to_email],
        "subject": f"Presença confirmada em {turma_nome}",
        "html": html_body,
        "text": f"Olá {aluno_nome}, sua presença em {turma_nome} foi registrada às {hora}. — Sistema SCPI",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
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
