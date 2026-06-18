import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import settings

_log = logging.getLogger(__name__)


def _send_smtp(to_email: str, subject: str, html: str, plain: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_user and settings.smtp_password:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, [to_email], msg.as_string())


class EmailService:
    async def send_activation_email(self, to_email: str, to_name: str, token: str) -> None:
        activation_url = f"{settings.app_base_url}/auth/activate"

        subject = "Activa tu cuenta en SVAES"

        plain = (
            f"Hola {to_name},\n\n"
            "Tu solicitud de acceso ha sido registrada. "
            "Para activar tu cuenta, haz clic en el siguiente enlace "
            "e introduce tu código de activación junto con tu nueva contraseña:\n\n"
            f"{activation_url}\n\n"
            f"Código de activación: {token}\n\n"
            "Este código expira en 24 horas.\n\n"
            "Si no solicitaste este acceso, ignora este mensaje.\n\n"
            "— Equipo SVAES"
        )

        html = f"""
        <html>
          <body style="font-family:IBM Plex Sans,Arial,sans-serif;background:#F6F4F0;padding:40px;">
            <div style="max-width:540px;margin:0 auto;background:#fff;border:1px solid #D4CFC7;border-radius:6px;padding:32px;">
              <h1 style="font-family:DM Serif Display,Georgia,serif;font-size:1.75rem;font-weight:400;color:#0D0F12;margin:0 0 16px;">
                Activa tu cuenta
              </h1>
              <p style="color:#7A7670;font-size:0.9375rem;line-height:1.65;margin:0 0 24px;">
                Hola <strong style="color:#0D0F12;">{to_name}</strong>,<br><br>
                Tu solicitud de acceso a <strong>SVAES</strong> ha sido registrada.
                Haz clic en el botón para ir a la página de activación e introduce tu código.
              </p>
              <a href="{activation_url}"
                 style="display:inline-block;background:#0D0F12;color:#F6F4F0;
                        text-decoration:none;padding:9px 18px;border-radius:4px;
                        font-size:0.6875rem;font-weight:600;letter-spacing:0.08em;
                        text-transform:uppercase;">
                Ir a activación
              </a>
              <div style="margin:24px 0;padding:16px;background:#F6F4F0;border:1px solid #D4CFC7;border-radius:4px;">
                <p style="font-family:IBM Plex Sans,Arial,sans-serif;font-size:0.6875rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#7A7670;margin:0 0 8px;">
                  Código de activación
                </p>
                <code style="font-family:IBM Plex Mono,monospace;font-size:0.9375rem;color:#0D0F12;word-break:break-all;user-select:all;">
                  {token}
                </code>
              </div>
              <p style="color:#7A7670;font-size:0.75rem;margin:24px 0 0;">
                Este código expira en 24 horas. Si no solicitaste este acceso, ignora este mensaje.
              </p>
            </div>
          </body>
        </html>
        """

        try:
            await asyncio.to_thread(_send_smtp, to_email, subject, html, plain)
            _log.info("Activation email sent to %s", to_email)
        except Exception:
            _log.exception("Failed to send activation email to %s", to_email)
            raise


    async def send_verification_result_email(
        self,
        to_email: str,
        to_name: str,
        release_name: str,
        verdict: str,
        release_id: str,
    ) -> None:
        verdict_labels = {
            "VALID": ("Válida", "#2D7A4F", "#E8F5ED"),
            "VALID_WITH_WARNINGS": ("Válida con advertencias", "#8B6914", "#FDF3DC"),
            "INVALID": ("No válida", "#C0392B", "#FDECEA"),
        }
        label, color, bg_color = verdict_labels.get(verdict, ("Desconocida", "#7A7670", "#F6F4F0"))

        release_url = f"{settings.app_base_url}/app/releases/{release_id}"
        subject = f"SVAES — Verificación completada: {release_name}"

        plain = (
            f"Hola {to_name},\n\n"
            f"La verificación de la entrega \"{release_name}\" ha finalizado.\n\n"
            f"Resultado: {label}\n\n"
            f"Consulta los detalles en: {release_url}\n\n"
            "— Equipo SVAES"
        )

        html = f"""
        <html>
          <body style="font-family:IBM Plex Sans,Arial,sans-serif;background:#F6F4F0;padding:40px;">
            <div style="max-width:540px;margin:0 auto;background:#fff;border:1px solid #D4CFC7;border-radius:6px;overflow:hidden;">
              <div style="background:#0D0F12;padding:24px 32px;">
                <span style="font-family:IBM Plex Sans,Arial,sans-serif;font-size:0.6875rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:rgba(232,213,163,0.85);">SVAES</span>
              </div>
              <div style="padding:32px;">
                <h1 style="font-family:DM Serif Display,Georgia,serif;font-size:1.75rem;font-weight:400;color:#0D0F12;margin:0 0 8px;line-height:1.2;">
                  Verificación completada
                </h1>
                <p style="color:#7A7670;font-size:0.9375rem;line-height:1.65;margin:0 0 24px;">
                  Hola <strong style="color:#0D0F12;">{to_name}</strong>,<br>
                  la verificación de la entrega <strong style="color:#0D0F12;">{release_name}</strong> ha finalizado.
                </p>
                <div style="display:inline-block;background:{bg_color};border:1px solid {color};border-radius:4px;padding:6px 14px;margin-bottom:24px;">
                  <span style="font-family:IBM Plex Sans,Arial,sans-serif;font-size:0.6875rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:{color};">{label}</span>
                </div>
                <br>
                <a href="{release_url}"
                   style="display:inline-block;background:#0D0F12;color:#F6F4F0;
                          text-decoration:none;padding:9px 18px;border-radius:4px;
                          font-size:0.6875rem;font-weight:600;letter-spacing:0.08em;
                          text-transform:uppercase;">
                  Ver detalles
                </a>
                <p style="color:#7A7670;font-size:0.75rem;margin:24px 0 0;">
                  Has recibido este correo porque tienes activadas las notificaciones de verificación en SVAES.
                </p>
              </div>
            </div>
          </body>
        </html>
        """

        try:
            await asyncio.to_thread(_send_smtp, to_email, subject, html, plain)
            _log.info("Verification result email sent to %s (verdict=%s)", to_email, verdict)
        except Exception:
            _log.exception("Failed to send verification result email to %s", to_email)


email_service = EmailService()
