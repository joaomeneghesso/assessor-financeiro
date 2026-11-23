import tempfile
import unittest
from datetime import date
from pathlib import Path

import database
import services
import telegram_experiencia as ux


class V403NovoFixoTests(unittest.TestCase):
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

    def test_fluxo_fixo_e_nativo_e_nao_vira_despesa(self):
        screen = self.exp.act(self.key, ('new_fixed_start',))
        self.assertIn('nome do fixo', screen.text.lower())
        self.assertEqual('new_fixed_name', self.exp.session(self.key).stage)

        self.exp.handle_text(self.key, 'YouTube Premium')
        self.exp.handle_text(self.key, '12,95')
        self.exp.act(self.key, ('new_fixed_answer', 'Assinaturas'))
        self.exp.act(self.key, ('new_fixed_answer', 'credito'))
        self.exp.handle_text(self.key, 'InfinitePay')
        self.exp.handle_text(self.key, '9')
        self.exp.act(self.key, ('new_fixed_answer', '2026-09'))
        preview = self.exp.act(self.key, ('new_fixed_no_end',))

        labels=[label for row in preview.rows for label,_ in row]
        self.assertIn('\u2705 Salvar fixo', labels)
        self.assertFalse(any('Salvar despesa' in label for label in labels))
        self.assertIn('Nenhuma despesa foi criada', preview.text)
        self.assertEqual([], list(database.buscar_transacoes_por_mes('2026-09')))

        done = self.exp.act(self.key, ('new_fixed_commit',))
        self.assertIn('Fixo cadastrado', done.text)
        self.assertIn('nao foi criado como despesa separada', ux.norm(done.text))
        self.assertEqual([], list(database.buscar_transacoes_por_mes('2026-09')))

        fixos = [dict(x) for x in database.listar_compromissos(tipo='fixo')]
        self.assertEqual(1, len(fixos))
        f = fixos[0]
        self.assertEqual('YouTube Premium', f['nome'])
        self.assertAlmostEqual(12.95, f['valor'])
        self.assertEqual('Assinaturas', f['categoria'])
        self.assertEqual('InfinitePay', f['conta_pagamento'])
        self.assertEqual('cr\u00e9dito', f['forma_pagamento'])
        self.assertEqual(9, f['dia_vencimento'])
        self.assertEqual('2026-09-01', f['data_inicio'])
        self.assertIsNone(f['data_fim'])

    def test_fixo_credito_entra_na_fatura_infinitepay(self):
        database.inserir_transacao({
            'data': '2026-09-10', 'tipo': 'despesa', 'valor': 131.34,
            'categoria': 'Outros', 'descricao': 'Compras InfinitePay',
            'conta': 'InfinitePay', 'forma_pagamento': 'cr\u00e9dito',
            'mensagem_original': 'fixture', 'parcelas_total': 1,
        })
        antes = services.calcular_fatura_unificada('2026-09', 'InfinitePay', somente_cartao=True)
        self.assertAlmostEqual(131.34, antes['saldo_restante'], places=2)

        result = services.cadastrar_fixo_guiado({
            'nome': 'YouTube Premium', 'valor': 12.95, 'categoria': 'Assinaturas',
            'forma_pagamento': 'credito', 'conta_pagamento': 'InfinitePay',
            'dia_vencimento': 9, 'data_inicio': '2026-09', 'data_fim': None,
        }, sessao='teste')
        self.assertAlmostEqual(131.34, result['fatura_antes'], places=2)
        self.assertAlmostEqual(144.29, result['fatura_depois'], places=2)

    def test_bloqueia_fixo_exatamente_duplicado(self):
        payload = {
            'nome': 'YouTube Premium', 'valor': 12.95, 'categoria': 'Assinaturas',
            'forma_pagamento': 'credito', 'conta_pagamento': 'InfinitePay',
            'dia_vencimento': 9, 'data_inicio': '2026-09', 'data_fim': None,
        }
        services.cadastrar_fixo_guiado(payload, sessao='teste')
        with self.assertRaisesRegex(ValueError, 'J.*existe um fixo equivalente'):
            services.cadastrar_fixo_guiado(payload, sessao='teste')
        self.assertEqual(1, len(database.listar_compromissos(tipo='fixo')))

    def test_pix_fixo_nao_mexe_saldo_ao_cadastrar(self):
        services.cadastrar_fixo_guiado({
            'nome': 'Internet', 'valor': 48.30, 'categoria': 'Moradia',
            'forma_pagamento': 'pix', 'conta_pagamento': 'Ita\u00fa',
            'dia_vencimento': 25, 'data_inicio': '2026-09', 'data_fim': None,
        }, sessao='teste')
        self.assertEqual([], list(database.buscar_transacoes_por_mes('2026-09')))

    def test_a_pagar_mostra_fatura_consolidada_sem_youtube_individual(self):
        database.inserir_transacao({
            'data': '2026-09-10', 'tipo': 'despesa', 'valor': 131.34,
            'categoria': 'Outros', 'descricao': 'Compras InfinitePay',
            'conta': 'InfinitePay', 'forma_pagamento': 'cr\u00e9dito',
            'mensagem_original': 'fixture', 'parcelas_total': 1,
        })
        services.cadastrar_fixo_guiado({
            'nome': 'YouTube Premium', 'valor': 12.95, 'categoria': 'Assinaturas',
            'forma_pagamento': 'credito', 'conta_pagamento': 'InfinitePay',
            'dia_vencimento': 9, 'data_inicio': '2026-09', 'data_fim': None,
        }, sessao='teste')
        items = self.exp.obligations('2026-09')
        self.assertFalse(any(i.get('nome') == 'YouTube Premium' for i in items), items)
        faturas = [i for i in items if ux.norm(i.get('nome')) == 'infinitepay']
        self.assertEqual(1, len(faturas), items)
        self.assertAlmostEqual(144.29, float(faturas[0]['valor']), places=2)

    def test_app_fixo_mensal_usa_wizard_nativo(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock
        import app

        update = SimpleNamespace(
            message=SimpleNamespace(text='', message_id=1, reply_text=mock.AsyncMock()),
            callback_query=None,
            effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=1),
        )
        tela = object()
        with mock.patch.object(app.ux, 'run_experience', mock.AsyncMock(return_value=tela)) as run, \
                mock.patch.object(app.ux, 'send_screen', mock.AsyncMock()) as enviar, \
                mock.patch.object(app, 'definir_pendencia_guiada', mock.Mock()) as pendencia:
            asyncio.run(app.iniciar_fluxo_guiado(update, SimpleNamespace(), 'registrar_fixo'))
        run.assert_awaited_once_with('act', app.ux.session_key(update), ('new_fixed_start',))
        self.assertIs(enviar.await_args.args[1], tela)
        pendencia.assert_not_called()


if __name__ == '__main__':
    unittest.main()
