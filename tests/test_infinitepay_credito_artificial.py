"""Regressões para compra coberta por crédito e conferência artificial de fatura."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import fatura_conferencia as conferencia
import services as svc
import telegram_experiencia as ux


class InfinitepayCreditoArtificialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        target = Path(self.tmp.name) / "fixture.db"
        for module in (db, svc):
            mocked = patch.object(module, "DB_PATH", target)
            mocked.start()
            self.addCleanup(mocked.stop)
        db.init_db()
        migration_path = Path(__file__).resolve().parents[1] / "migrations" / "0004_competencia_faturas.py"
        spec = importlib.util.spec_from_file_location("fixture_competencia_infinitepay", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with db.get_connection() as conn:
            migration.upgrade(conn)
        self.engine = ux.Experience(date_provider=lambda: date(2026, 10, 7))
        self.key = "infinitepay"

    def compra(self, mes, valor, descricao="Compra"):
        return db.inserir_transacao({
            "data": mes + "-07",
            "tipo": "despesa",
            "valor": valor,
            "categoria": "Eletrônicos",
            "descricao": descricao,
            "conta": "Infinitepay",
            "forma_pagamento": "crédito",
            "parcelas_total": 1,
            "data_compra": mes + "-07",
            "competencia_fatura": mes,
        })

    def test_conferencia_neutraliza_credito_artificial_e_outubro_fica_a_pagar(self):
        self.compra("2026-09", 299.35, "Compras de setembro")
        movimento_id = db.inserir_fatura_movimento({
            "ano_mes": "2026-09",
            "conta_cartao": "Infinitepay",
            "tipo_movimento": "pagamento_total",
            "valor": 362.29,
            "data_movimento": "2026-09-27",
            "conta_origem": "Mercado Pago",
            "descricao": "Pagamento real",
        })
        movimento = dict(db.buscar_fatura_movimento_por_id(movimento_id))
        previa = comp.calcular_fatura_unificada("2026-09", "Infinitepay", somente_cartao=True)
        evento = conferencia.confirmar(
            "2026-09", "Infinitepay", movimento_id, 362.29,
            movimento, previa, "teste", "Diferença artificial de composição",
        )

        self.assertAlmostEqual(62.94, evento["ajuste_composicao"], places=2)
        setembro = comp.calcular_fatura_unificada("2026-09", "Infinitepay", somente_cartao=True)
        self.assertAlmostEqual(0.0, setembro["saldo_restante"], places=2)
        self.assertAlmostEqual(0.0, comp.calcular_resumo_pagamento_conta("2026-09", "Infinitepay")["saldo_fatura"], places=2)

        self.compra("2026-10", 41.88, "e-mail corporativo Empresa X")
        outubro = comp.calcular_resumo_pagamento_conta("2026-10", "Infinitepay")
        self.assertAlmostEqual(41.88, outubro["fatura_bruta"], places=2)
        self.assertAlmostEqual(41.88, outubro["fatura"], places=2)
        self.assertAlmostEqual(0.0, outubro["credito_herdado"], places=2)

    def test_conta_com_compra_coberta_por_credito_continua_visivel(self):
        self.compra("2026-09", 100.00)
        db.inserir_fatura_movimento({
            "ano_mes": "2026-09", "conta_cartao": "Infinitepay",
            "tipo_movimento": "pagamento_total", "valor": 150.00,
            "data_movimento": "2026-09-20", "conta_origem": "Mercado Pago",
        })
        self.compra("2026-10", 30.00)

        screen = self.engine.act(self.key, ("pay_month", "2026-10"))
        self.assertIn("Infinitepay", screen.text)
        actions = [action for row in screen.rows for _, action in row]
        self.assertTrue(any(action[0] == "pay_month_expand" and action[1] == "Infinitepay" for action in actions))

    def test_botao_pos_registro_abre_detalhe_da_conta_escolhida(self):
        draft = {
            "key": "evento-1", "tipo": "despesa", "valor": 41.88,
            "descricao": "e-mail corporativo Empresa X", "categoria": "Eletrônicos",
            "conta": "Infinitepay", "forma_pagamento": "crédito",
            "data": "2026-10-07", "parcelas_total": 1,
            "competencia_fatura": "2026-10", "sem_vinculo_confirmado": True,
        }
        session = self.engine.session(self.key)
        session.draft = draft
        session.stage = "confirm"
        screen = self.engine.act(self.key, ("commit", "evento-1"))
        actions = [action for row in screen.rows for _, action in row]
        self.assertIn(("pay_account_detail", "Infinitepay", "2026-10"), actions)


if __name__ == "__main__":
    unittest.main()
