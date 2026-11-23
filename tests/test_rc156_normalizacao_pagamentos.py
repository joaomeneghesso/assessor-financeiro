import contextlib
import importlib.util
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compromissos
import database
import services
from pagamentos_canonicos import obter_conta_pagamento_efetiva

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("migration_runner_rc156", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class NormalizacaoPagamentosRC156Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "financeiro.db"
        self.migrations = self.root / 'migrations'
        self.migrations.mkdir()
        for source in (ROOT/'migrations').glob('[0-9][0-9][0-9][0-9]_*.py'):
            if int(source.name[:4]) <= 2:
                shutil.copy2(source, self.migrations/source.name)
        with patch.object(database, 'DB_PATH', self.db):
            database.init_db()
        # A fixture deve estar na versao 2, e nao em uma copia ja normalizada.
        runner.apply_migrations(self.db,self.migrations,self.root/'fixture_backups')
        shutil.copy2(ROOT/'migrations/0003_normalizacao_pagamentos_historicos.py',self.migrations/'0003_normalizacao_pagamentos_historicos.py')
        expected = [
            (4,'CNPJ (baixa)','Pix','pix',51.53),
            (5,'Condominio','Pix','pix',231.45),
            (6,'IPTU','Pix','pix',53.60),(7,'IPTV','Pix','pix',8.00),
            (8,'Internet','Pix','pix',48.30),(10,'iCloud','Lia','crédito',33.45),
            (30,'Empréstimos','Pix','pix',400.00),(43,'Tag condomínio','Pix','pix',30.00)]
        with contextlib.closing(sqlite3.connect(self.db)) as con:
            for ident,name,account,method,value in expected:
                con.execute('INSERT INTO compromissos (id,tipo,nome,categoria,conta_pagamento,forma_pagamento,valor,data_inicio,ativo,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (ident,'fixo',name,'Teste',account,method,value,'2026-07-01',1,'2026-07-01','2026-07-01'))
            con.commit()
        self.backups = self.root / "backups"

    def tearDown(self):
        self.tmp.cleanup()

    def test_migration_0003_normaliza_somente_os_oito_registros(self):
        before = {}
        with contextlib.closing(sqlite3.connect(self.db)) as c:
            c.row_factory = sqlite3.Row
            before = {r["id"]: dict(r) for r in c.execute("SELECT * FROM compromissos ORDER BY id")}
        result = runner.apply_migrations(self.db, self.migrations, self.backups, executed_by="teste_rc156")
        self.assertEqual(3, result["current_version"])
        with contextlib.closing(sqlite3.connect(self.db)) as c:
            c.row_factory = sqlite3.Row
            after = {r["id"]: dict(r) for r in c.execute("SELECT * FROM compromissos ORDER BY id")}
            self.assertEqual(3, c.execute("PRAGMA user_version").fetchone()[0])
        changed = {ident for ident in before if before[ident] != after[ident]}
        self.assertEqual({4, 5, 6, 7, 8, 10, 30, 43}, changed)
        for ident in {4, 5, 6, 7, 8, 30, 43}:
            self.assertEqual("Itaú", after[ident]["conta_origem"])
            self.assertIsNone(after[ident]["destino_pagamento"])
            self.assertEqual(before[ident]["conta_pagamento"], after[ident]["conta_pagamento"])
            self.assertEqual(before[ident]["forma_pagamento"], after[ident]["forma_pagamento"])
            self.assertEqual(before[ident]["valor"], after[ident]["valor"])
        self.assertEqual("Itaú", after[10]["conta_origem"])
        self.assertEqual("Lia", after[10]["destino_pagamento"])
        self.assertEqual("crédito", after[10]["forma_pagamento"])
        self.assertEqual("Lia", after[10]["conta_pagamento"])

    def test_migration_aborta_se_conjunto_historico_divergir(self):
        with contextlib.closing(sqlite3.connect(self.db)) as c:
            c.execute("UPDATE compromissos SET valor=999 WHERE id=4")
            c.commit()
        with self.assertRaises(runner.MigrationError):
            runner.apply_migrations(self.db, self.migrations, self.backups, executed_by="teste_rc156")
        with contextlib.closing(sqlite3.connect(self.db)) as c:
            self.assertEqual(2, c.execute("PRAGMA user_version").fetchone()[0])
            self.assertEqual(999, c.execute("SELECT valor FROM compromissos WHERE id=4").fetchone()[0])

    def test_conta_canonica_tem_prioridade_e_legado_e_fallback(self):
        self.assertEqual("Itaú", obter_conta_pagamento_efetiva({"conta_origem": "Itaú", "conta_pagamento": "Pix"}))
        self.assertEqual("Nubank", obter_conta_pagamento_efetiva({"conta_origem": None, "conta_pagamento": "Nubank"}))

    def test_projecao_e_checklist_usam_itau_sem_transformar_pix_em_fatura(self):
        item = {
            "origem": "compromisso", "id": 4, "tipo": "fixo", "nome": "CNPJ (baixa)",
            "categoria": "Outros", "conta_pagamento": "Itaú", "conta_origem": "Itaú",
            "conta_pagamento_legado": "Pix", "destino_pagamento": None,
            "forma_pagamento": "pix", "valor": 51.53, "data": "2026-07-10",
            "parcela_atual": None, "parcelas_total": None, "ativo": True,
        }
        with patch.object(services, "projetar_pagamentos_mes", return_value=[item]), \
             patch.object(services, "buscar_checklist_datas_pagamento_mes", return_value={}), \
             patch.object(services, "buscar_checklist_datas_pagamento_padrao", return_value={}):
            itens = services.montar_itens_checklist_mes("2026-07", modo="geral")
        self.assertEqual(1, len(itens))
        self.assertEqual("Itaú", itens[0]["conta"])
        self.assertEqual("pix", itens[0]["forma"])
        self.assertEqual("individuais", itens[0]["grupo"])
        self.assertNotEqual("Pix", itens[0]["conta"])

    def test_fixos_exibem_conta_forma_e_destino_separados(self):
        registro = {
            "id": 10, "nome": "iCloud", "valor": 33.45, "dia_vencimento": 15,
            "conta_pagamento": "Lia", "conta_origem": "Itaú",
            "forma_pagamento": "crédito", "destino_pagamento": "Lia",
            "categoria": "Assinaturas", "ativo": 1,
            "tipo": "fixo", "data_inicio": "2000-01-01", "data_fim": None,
        }
        with patch.object(compromissos, "listar_compromissos", return_value=[registro]):
            texto = compromissos.listar_fixos_formatado()
        self.assertIn("Conta: Itaú", texto)
        self.assertIn("Forma: crédito", texto)
        self.assertIn("Destino: Lia", texto)
        self.assertNotIn("🏦 Lia", texto)


if __name__ == "__main__":
    unittest.main()
