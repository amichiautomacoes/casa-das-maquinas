"""Credenciais Base64 de producao sem dependencia de arquivos locais."""

import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from visualizacao.auth import load_credentials


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.info = {
            "type": "service_account",
            "project_id": "example-project",
            "client_email": "teste@example.iam.gserviceaccount.com",
            "private_key": "CHAVE-DE-TESTE",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

    def test_base64_json_is_self_contained_without_local_file_or_extra_environment(self):
        encoded = base64.b64encode(json.dumps(self.info).encode("utf-8")).decode("ascii")
        with patch("visualizacao.auth._read_json", side_effect=AssertionError("Nao pode ler JSON local")):
            with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
                credentials = load_credentials({"GOOGLE_APPLICATION_CREDENTIALS": encoded})
        self.assertIs(credentials, constructor.return_value)
        self.assertEqual(constructor.call_args.args[0], self.info)

    def test_base64_pem_uses_explicit_account_metadata(self):
        pem = "-----BEGIN PRIVATE KEY-----\\nCHAVE-DE-TESTE\\n-----END PRIVATE KEY-----"
        encoded = base64.b64encode(pem.encode("utf-8")).decode("ascii")
        with patch("visualizacao.auth._read_json", side_effect=AssertionError("Nao pode ler JSON local")):
            with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
                load_credentials({
                    "GOOGLE_APPLICATION_CREDENTIALS": encoded,
                    "GCP_SERVICE_ACCOUNT_EMAIL": self.info["client_email"],
                    "GCP_PROJECT_ID": self.info["project_id"],
                })
        received = constructor.call_args.args[0]
        self.assertEqual(received["client_email"], self.info["client_email"])
        self.assertEqual(received["private_key"], pem.replace("\\n", "\n"))

    def test_plain_json_remains_supported(self):
        with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
            load_credentials({"GOOGLE_APPLICATION_CREDENTIALS": json.dumps(self.info)})
        self.assertEqual(constructor.call_args.args[0], self.info)

    def test_mounted_json_file_remains_supported(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "service-account.json"
            path.write_text(json.dumps(self.info), encoding="utf-8")
            with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
                load_credentials({"GOOGLE_APPLICATION_CREDENTIALS": str(path)})
        self.assertEqual(constructor.call_args.args[0], self.info)

    def test_corrupted_or_unsupported_base64_does_not_expose_the_value(self):
        values = [
            "credencial-corrompida!",
            base64.b64encode(b"invalid-secret-content").decode("ascii"),
            base64.b64encode(b'{"private_key": "secret",').decode("ascii"),
            base64.b64encode(b"\xff\xfe\xff").decode("ascii"),
        ]
        with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
            for value in values:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError) as error:
                        load_credentials({"GOOGLE_APPLICATION_CREDENTIALS": value})
                    self.assertNotIn(value, str(error.exception))
                    self.assertNotIn("secret", str(error.exception))
        constructor.assert_not_called()

    def test_incomplete_base64_json_reports_missing_fields_before_loading_the_key(self):
        incomplete = {"type": "service_account", "private_key": "CHAVE-DE-TESTE"}
        encoded = base64.b64encode(json.dumps(incomplete).encode("utf-8")).decode("ascii")
        with patch("visualizacao.auth.service_account.Credentials.from_service_account_info") as constructor:
            with self.assertRaisesRegex(ValueError, "client_email, token_uri"):
                load_credentials({"GOOGLE_APPLICATION_CREDENTIALS": encoded})
        constructor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
