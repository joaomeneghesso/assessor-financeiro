"""Configuração única (Onda 3, etapa 1C): ``config.py`` x código x ``.env.example``.

- toda variável ``ASSESSOR_*``/``TELEGRAM_*`` citada no código de produção está
  em ``config.VARIAVEIS`` e documentada no ``.env.example`` (ativa ou comentada),
  e vice-versa;
- ``config.ler*`` lê o ambiente do processo a cada chamada (``patch.dict``);
- importar ``config`` não carrega o ``.env``;
- caminhos ancorados na pasta do projeto, com os apelidos antigos preservados.
"""
import ast
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import config

RAIZ = Path(__file__).resolve().parents[1]
_NOME = re.compile(r"^(ASSESSOR|TELEGRAM)_[A-Z0-9_]+$")
_LINHA_EXEMPLO = re.compile(r"^\s*#?\s*((?:ASSESSOR|TELEGRAM)_[A-Z0-9_]+)\s*=", re.MULTILINE)


def variaveis_no_codigo():
    nomes = set()
    for arq in RAIZ.glob("*.py"):
        if arq.name.startswith("test_") or arq.stem in {"release_harness", "config"}:
            continue
        for no in ast.walk(ast.parse(arq.read_text(encoding="utf-8-sig"))):
            if isinstance(no, ast.Constant) and isinstance(no.value, str) and _NOME.match(no.value):
                nomes.add(no.value)
    return nomes


def variaveis_no_exemplo():
    return set(_LINHA_EXEMPLO.findall((RAIZ / ".env.example").read_text(encoding="utf-8")))


class ConfigUnicaTest(unittest.TestCase):
    def test_codigo_registro_e_exemplo_batem(self):
        codigo, exemplo, registro = variaveis_no_codigo(), variaveis_no_exemplo(), set(config.VARIAVEIS)
        self.assertEqual(sorted(codigo - registro), [], "variável lida no código fora de config.VARIAVEIS")
        self.assertEqual(sorted(registro - codigo), [], "config.VARIAVEIS tem variável que ninguém lê")
        self.assertEqual(sorted(registro - exemplo), [], "variável lida sem documentação no .env.example")
        self.assertEqual(sorted(exemplo - registro), [], ".env.example documenta variável que o código não lê")

    def test_timezone_sinalizada_como_ignorada(self):
        texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
        self.assertIn("# ASSESSOR_TIMEZONE=", texto)
        self.assertNotRegex(texto, r"(?m)^ASSESSOR_TIMEZONE=")
        self.assertIn("IGNORADA", config.VARIAVEIS["ASSESSOR_TIMEZONE"])

    def test_leitura_acompanha_o_ambiente_e_mantem_padroes(self):
        with patch.dict(os.environ, {"ASSESSOR_AUTOLOCK_MINUTES": "7", "ASSESSOR_ALLOW_GROUPS": " Sim "}):
            self.assertEqual(config.ler_int("ASSESSOR_AUTOLOCK_MINUTES", "15"), 7)
            self.assertTrue(config.ler_bool("ASSESSOR_ALLOW_GROUPS", "false"))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.ler_int("ASSESSOR_AUTOLOCK_MINUTES", "15"), 15)
            self.assertFalse(config.ler_bool("ASSESSOR_ALLOW_GROUPS", "false"))
            self.assertIsNone(config.ler("TELEGRAM_ALLOWED_USER_ID"))
            config.definir("ASSESSOR_PIN_LENGTH", "6")
            self.assertEqual(config.ler("ASSESSOR_PIN_LENGTH"), "6")
            config.remover("ASSESSOR_PIN_LENGTH")
            config.remover("ASSESSOR_PIN_LENGTH")  # idempotente
            self.assertFalse(config.existe("ASSESSOR_PIN_LENGTH"))

    def test_importar_config_nao_carrega_dotenv(self):
        arvore = ast.parse((RAIZ / "config.py").read_text(encoding="utf-8"))
        chamadas_topo = [no for no in arvore.body if isinstance(no, ast.Expr) and isinstance(no.value, ast.Call)]
        self.assertEqual(chamadas_topo, [])

    def test_caminhos_ancorados_e_apelidos_preservados(self):
        import compromissos
        import database
        import services
        self.assertEqual(config.BASE_DIR, RAIZ)
        for pasta, nome in ((config.BACKUPS_DIR, "backups"), (config.EXPORTS_DIR, "exports"),
                            (config.DASHBOARDS_DIR, "dashboards"), (config.IMPORTS_DIR, "imports")):
            self.assertTrue(pasta.is_absolute())
            self.assertEqual(pasta, RAIZ / nome)
        self.assertEqual(config.DB_PATH, RAIZ / "data" / "financeiro.db")
        self.assertEqual(compromissos.IMPORTS_DIR, config.IMPORTS_DIR)
        # tests/__init__.py redireciona os apelidos para a pasta temporária: continuam patcháveis
        self.assertTrue(hasattr(services, "BACKUPS_DIR") and hasattr(services, "EXPORTS_DIR") and hasattr(services, "DASHBOARDS_DIR"))
        self.assertNotEqual(database.DB_PATH, config.DB_PATH)


if __name__ == "__main__":
    unittest.main()
