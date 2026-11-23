import tempfile
import unittest
from datetime import date
from pathlib import Path

import database
import services
import telegram_experiencia as ux


class V402IntegridadeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_services_db = services.DB_PATH
        self.db = Path(self.tmp.name) / 'financeiro.db'
        database.DB_PATH = self.db
        services.DB_PATH = self.db
        database.init_db()
        self.exp = ux.Experience(date_provider=lambda: date(2026, 9, 24))
        self.key = 'user:chat'

    def tearDown(self):
        database.DB_PATH = self.old_db
        services.DB_PATH = self.old_services_db
        self.tmp.cleanup()

    def inserir_compromisso(self, **overrides):
        base = {
            'tipo': 'fixo',
            'nome': 'Conta teste',
            'categoria': 'Teste',
            'conta_pagamento': 'Itaú',
            'forma_pagamento': 'pix',
            'valor': 50.0,
            'dia_vencimento': 10,
            'data_inicio': '2026-06-01',
            'data_fim': None,
            'ativo': True,
            'origem': 'fixture_v402',
        }
        base.update(overrides)
        return database.inserir_compromisso(base)

    def test_credito_individual_antigo_nao_vira_pendencia_herdada(self):
        self.inserir_compromisso(
            nome='YouTube premium', conta_pagamento='Infinitepay',
            forma_pagamento='crédito', valor=13.13,
            dia_vencimento=25, data_inicio='2026-06-25', data_fim='2026-08-31')
        pend = services.listar_pendencias_abertas_anteriores('2026-09')
        self.assertFalse(any(i.get('nome') == 'YouTube premium' for i in pend), pend)

    def test_obligations_nao_expoe_credito_individual_historico(self):
        self.inserir_compromisso(
            nome='YouTube premium', conta_pagamento='Infinitepay',
            forma_pagamento='crédito', valor=13.13,
            dia_vencimento=25, data_inicio='2026-06-25', data_fim='2026-08-31')
        items = self.exp.obligations('2026-08')
        self.assertFalse(any(i.get('nome') == 'YouTube premium' for i in items), items)

    def test_settlement_credito_e_bloqueado_sem_criar_despesa(self):
        ident = self.inserir_compromisso(
            nome='Assinatura cartão', conta_pagamento='Infinitepay',
            forma_pagamento='crédito', valor=13.13,
            data_inicio='2026-09-01', dia_vencimento=20)
        antes = len(list(database.buscar_transacoes_por_mes('2026-09')))
        screen = self.exp.begin_settlement(self.key, ident, '2026-09')
        depois = len(list(database.buscar_transacoes_por_mes('2026-09')))
        self.assertEqual(antes, depois)
        self.assertIn('fatura do cartão', screen.text.lower())
        self.assertIsNone(self.exp.session(self.key).draft)

    def test_settlement_pix_continua_disponivel(self):
        ident = self.inserir_compromisso(
            nome='Condomínio', conta_pagamento='Itaú',
            forma_pagamento='pix', valor=231.45,
            data_inicio='2026-09-01', dia_vencimento=20)
        screen = self.exp.begin_settlement(self.key, ident, '2026-09')
        draft = self.exp.session(self.key).draft
        self.assertIsNotNone(draft)
        self.assertEqual('despesa', draft['tipo'])
        self.assertEqual(231.45, draft['valor'])
        self.assertNotIn('pertence à fatura do cartão', screen.text.lower())

    def test_central_e_filtro_vencidas_usam_mesma_colecao(self):
        self.inserir_compromisso(
            nome='Conta vencida', conta_pagamento='Itaú',
            forma_pagamento='pix', valor=80.0,
            data_inicio='2026-09-01', dia_vencimento=10)
        s = self.exp.session(self.key)
        s.month = '2026-09'
        data = __import__('assessor_orientacao').coletar(self.exp, s)
        self.assertEqual(1, len(data['overdue']))
        s.pay_filter = 'overdue'
        tela = self.exp.screen_pay(s)
        self.assertIn('R$ 80,00', tela.text)
        self.assertIn('1 item', tela.text)  # plural(): '(ns)' foi substituído na Fase 1
        self.assertIn('Conta vencida', tela.text)


if __name__ == '__main__':
    unittest.main()
