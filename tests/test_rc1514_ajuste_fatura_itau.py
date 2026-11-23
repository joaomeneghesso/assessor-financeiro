import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ajustar_fatura_itau import aplicar
import database
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DB_ORIG = ROOT / "data" / "financeiro.db"


class TestRC1514AjusteFaturaItau(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "financeiro.db"
        # Fixture explicita: os tres fixos somam exatamente 154.83.
        # Este teste nunca le o banco pessoal da instalacao.
        with patch.object(database, 'DB_PATH', self.db):
            database.init_db()
            for name,value in [('Wellhub teste',91.70),('Celular teste',50.00),('YouTube teste',13.13)]:
                database.inserir_compromisso(dict(tipo='fixo',nome=name,categoria='Assinaturas',
                    conta_pagamento='Itaú',forma_pagamento='crédito',valor=value,
                    data_inicio='2026-07-01',dia_vencimento=10,ativo=True))
            with database.get_connection() as con:
                for ident,method in [(90,'crédito'),(100,'pix')]:
                    con.execute('INSERT INTO transacoes (id,data,tipo,valor,categoria,descricao,conta,forma_pagamento,criado_em) VALUES (?,?,?,?,?,?,?,?,?)',
                        (ident,'2026-07-15','despesa',10,'Teste','Compra teste','Itaú',method,'2026-07-15'))
            database.inserir_fatura_movimento(dict(ano_mes='2026-07',conta_cartao='Itaú',
                tipo_movimento='credito',valor=5,data_movimento='2026-07-15'))

    def tearDown(self):
        self.tmp.cleanup()

    def test_somente_credito_itau_e_postergado(self):
        con = sqlite3.connect(self.db)
        antes_pix = con.execute("SELECT data FROM transacoes WHERE id=100").fetchone()[0]
        antes_credito = con.execute("SELECT data FROM transacoes WHERE id=90").fetchone()[0]
        con.close()

        aplicar(self.db, confirmar=True)

        con = sqlite3.connect(self.db)
        depois_pix = con.execute("SELECT data FROM transacoes WHERE id=100").fetchone()[0]
        depois_credito = con.execute("SELECT data FROM transacoes WHERE id=90").fetchone()[0]
        con.close()
        self.assertEqual(antes_pix, depois_pix)
        self.assertEqual(depois_credito, "2026-08-15")

    def test_fixos_sao_duplicados_e_originais_preservados(self):
        aplicar(self.db, confirmar=True)
        con = sqlite3.connect(self.db)
        originais = con.execute("SELECT COUNT(*) FROM compromissos WHERE id IN (1,2,3)").fetchone()[0]
        duplicados = con.execute("SELECT COUNT(*) FROM compromissos WHERE origem=?", ("itau_fatura_2026_07_postergacao_1_mes",)).fetchone()[0]
        valor = con.execute("SELECT ROUND(SUM(valor),2) FROM compromissos WHERE origem=?", ("itau_fatura_2026_07_postergacao_1_mes",)).fetchone()[0]
        con.close()
        self.assertEqual(originais, 3)
        self.assertEqual(duplicados, 3)
        self.assertEqual(valor, 154.83)

    def test_movimentos_da_fatura_acompanham_a_competencia(self):
        con = sqlite3.connect(self.db)
        ids = [r[0] for r in con.execute("SELECT id FROM fatura_movimentos WHERE ano_mes='2026-07' AND lower(conta_cartao)='itaú'")]
        con.close()
        aplicar(self.db, confirmar=True)
        con = sqlite3.connect(self.db)
        meses = [r[0] for r in con.execute(f"SELECT ano_mes FROM fatura_movimentos WHERE id IN ({','.join('?'*len(ids))})", ids)] if ids else []
        con.close()
        self.assertEqual(["2026-08"], meses)

    def test_execucao_dupla_e_bloqueada(self):
        aplicar(self.db, confirmar=True)
        with self.assertRaises(RuntimeError):
            aplicar(self.db, confirmar=True)


if __name__ == "__main__":
    unittest.main()
