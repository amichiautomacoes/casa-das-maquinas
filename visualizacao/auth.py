"""Carrega credenciais apenas no servidor; suporta .env local e EasyPanel."""

import base64
import binascii
import json
from pathlib import Path

from google.oauth2 import service_account

from .config import PROJECT_ROOT, read_environment


SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
LOCAL_SERVICE_ACCOUNT_FILE = "casa-das-maquinas-a8aeb8e4800f.json"


def _read_json(path: Path) -> dict:
    try:
        info = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("Nao foi possivel ler o JSON da conta de servico.") from None
    if not isinstance(info, dict):
        raise ValueError("O JSON da conta de servico precisa ser um objeto.")
    return info


def load_credentials(environment: dict[str, str] | None = None) -> service_account.Credentials:
    env = read_environment() if environment is None else environment
    value = env.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not value:
        raise ValueError("Defina GOOGLE_APPLICATION_CREDENTIALS no .env ou no ambiente do container.")

    if not value.startswith(("{", "-----BEGIN PRIVATE KEY-----")):
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8-sig").strip()
        except (binascii.Error, UnicodeDecodeError, ValueError):
            # Mantem o suporte a caminhos de arquivos JSON montados no container.
            decoded = None
        if decoded is not None:
            if not decoded.startswith(("{", "-----BEGIN PRIVATE KEY-----")):
                raise ValueError("O Base64 das credenciais precisa conter um JSON de conta de servico ou uma chave PEM.")
            value = decoded

    if value.startswith("{"):
        try:
            info = json.loads(value)
        except json.JSONDecodeError:
            raise ValueError("O JSON das credenciais no ambiente e invalido.") from None
    elif value.startswith("-----BEGIN PRIVATE KEY-----"):
        # O ambiente de producao pode fornecer todos os campos sem copiar o JSON.
        info = {}
        if not env.get("GCP_SERVICE_ACCOUNT_EMAIL"):
            path = Path(env.get("GCP_SERVICE_ACCOUNT_FILE", LOCAL_SERVICE_ACCOUNT_FILE))
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if path.is_file():
                info = _read_json(path)
        info.update(
            type="service_account",
            private_key=value.replace("\\n", "\n"),
            client_email=env.get("GCP_SERVICE_ACCOUNT_EMAIL") or info.get("client_email"),
            project_id=env.get("GCP_PROJECT_ID") or info.get("project_id"),
            token_uri=env.get("GCP_TOKEN_URI") or info.get("token_uri") or "https://oauth2.googleapis.com/token",
        )
        # Um PEM atualizado pode pertencer a outra chave ativa da mesma conta.
        info.pop("private_key_id", None)
    else:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        info = _read_json(path)

    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise ValueError("Use credenciais de uma conta de servico do Google Cloud.")
    missing = [field for field in ("client_email", "private_key", "token_uri") if not info.get(field)]
    if missing:
        raise ValueError("Campos ausentes nas credenciais: " + ", ".join(missing))
    try:
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    except (ValueError, TypeError):
        raise ValueError("Nao foi possivel carregar a chave privada da conta de servico.") from None
