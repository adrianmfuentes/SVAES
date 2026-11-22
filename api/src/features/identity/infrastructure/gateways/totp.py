import base64
import io

import pyotp
import segno


class PyotpTotpService:
    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def provisioning_uri(self, secret: str, email: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="SVAES")

    def verify(self, secret: str, code: str) -> bool:
        return pyotp.TOTP(secret).verify(code, valid_window=1)


class SvgQrRenderer:
    def render_data_url(self, uri: str) -> str:
        buffer = io.BytesIO()
        segno.make_qr(uri).save(buffer, kind="svg", scale=4, border=1)
        return "data:image/svg+xml;base64," + base64.b64encode(buffer.getvalue()).decode()
