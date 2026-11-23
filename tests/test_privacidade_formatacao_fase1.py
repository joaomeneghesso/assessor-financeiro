"""Fase 1 do layout: privacidade em todas as telas, helpers de formatação e rótulos.

Banco temporário; nada toca data/financeiro.db.
"""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux
from telegram_design import (button_label, due_chip, mask_money, money_sinal, pct, plural,
                             present_text)

HOJE = date(2026, 9, 30)
VALOR = re.compile(r'R\$\s*-?\d')
# Telas de consulta que mostram valores: todas devem respeitar "Ocultar".
VIEWS = ('home', 'balance', 'balance_details', 'pay', 'history', 'closing', 'closing_details',
         'analytics', 'categories', 'budgets', 'agenda', 'attention', 'plan', 'month_actions',
         'receivables', 'reconciliations', 'review', 'review_details')


class FormatacaoPuraTests(unittest.TestCase):
    def test_plural(self):
        self.assertEqual('1 conta', plural(1, 'conta'))
        self.assertEqual('3 contas', plural(3, 'conta'))
        self.assertEqual('0 contas', plural(0, 'conta'))
        self.assertEqual('1 item', plural(1, 'item', 'itens'))
        self.assertEqual('2 itens', plural(2, 'item', 'itens'))
        self.assertEqual('2 obrigações', plural(2, 'obrigação', 'obrigações'))

    def test_valor_negativo_usa_sinal_de_menos_antes_do_simbolo(self):
        self.assertEqual('−R$ 1.234,56', money_sinal('R$ -1.234,56'))
        self.assertEqual('R$ 50,00', money_sinal('R$ 50,00'))
        self.assertEqual('−R$ 1.234,56', ux.money(-1234.56))
        self.assertEqual('R$ 2.345,67', ux.money(2345.67))

    def test_services_continua_com_formato_antigo(self):
        # tests/test_bloco_b_fatura_telas.py depende deste formato em services.
        self.assertEqual('R$ -50,00', svc.formatar_moeda(-50.0))

    def test_percentual_com_virgula(self):
        self.assertEqual('277,2%', pct(277.2))
        self.assertEqual('5,0%', pct(5))
        self.assertEqual('12%', pct(12, 0))

    def test_chip_de_vencimento(self):
        self.assertEqual('🔴', due_chip(-3))
        self.assertEqual('🟡', due_chip(0))
        self.assertEqual('🟡', due_chip(1))
        self.assertEqual('⚪', due_chip(2))
        self.assertEqual('⚪', due_chip(30))

    def test_mask_money(self):
        self.assertEqual('Total: ••••', mask_money('Total: R$ 1.234,56'))
        self.assertEqual('↘ Uber · ••••', mask_money('↘ Uber · − R$ 57,40'))
        self.assertEqual('Saldo ••••', mask_money('Saldo −R$ 1.234,56'))
        self.assertEqual('Energia · 210,00', mask_money('Energia · 210,00'))
        self.assertEqual('Energia · ••••', mask_money('Energia · 210,00', bare=True))
        self.assertEqual('3 contas · 25%', mask_money('3 contas · 25%', bare=True))

    def test_icones_de_pagamento_distintos_e_sem_clipboard_padrao(self):
        icones = {nome: button_label(nome, ('answer', nome)).split(' ')[0]
                  for nome in ('Pix', 'Débito', 'Dinheiro', 'Transferência', 'Boleto', 'Crédito')}
        self.assertEqual(len(icones), len(set(icones.values())), icones)
        self.assertNotIn('💸', icones.values())

    def test_titulo_desconhecido_nao_ganha_clipboard(self):
        self.assertNotIn('📋', present_text('<b>Essa despesa foi parcelada?</b>\nEscolha.'))
        self.assertNotIn('📋', present_text('<b>Qualquer título novo</b>'))
        self.assertTrue(present_text('<b>Central de atenção · Outubro 2026</b>').startswith('<b>🔎 Central'))
        self.assertTrue(present_text('<b>Limites de gastos</b>').startswith('<b>🎯'))
        # idempotente
        for texto in ('<b>Central de atenção</b>\nx', '<b>Essa despesa foi parcelada?</b>'):
            self.assertEqual(present_text(texto), present_text(present_text(texto)))


class TelasBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        for d, v, cat, desc, conta, forma in (
                ('2026-09-03', 120.5, 'Mercado', 'Mercado', 'Itaú', 'pix'),
                ('2026-09-10', 45, 'Transporte', 'Uber', 'Itaú', 'pix'),
                ('2026-09-12', 300, 'Lazer', 'Cinema', 'Nubank', 'crédito')):
            db.inserir_transacao(dict(data=d, tipo='despesa', valor=v, categoria=cat, descricao=desc,
                                      conta=conta, forma_pagamento=forma, parcelas_total=1))
        db.inserir_transacao(dict(data='2026-09-05', tipo='receita', valor=5000, categoria='Salário',
                                  descricao='Salário', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        db.inserir_compromisso(dict(tipo='fixo', nome='Internet', categoria='Casa', valor=80,
                                    data_inicio='2026-09-01', dia_vencimento=25,
                                    conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))
        db.inserir_compromisso(dict(tipo='fixo', nome='Energia', categoria='Casa', valor=210,
                                    data_inicio='2026-09-01', dia_vencimento=1,
                                    conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))
        db.definir_meta('Mercado', 100)
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = 'teste-fase1'

    def tela(self, acao, privacy):
        self.engine.sessions.pop(self.key, None)
        s = self.engine.session(self.key)
        s.privacy = privacy
        return self.engine.act(self.key, acao)

    @staticmethod
    def tudo(screen):
        partes = [screen.text, screen.rich_html or '']
        partes += [label for row in screen.rows for label, _ in row]
        return '\n'.join(partes)


class PrivacidadeTelasTests(TelasBase):
    def test_nenhuma_tela_mostra_valor_com_ocultar_ligado(self):
        vazadas = {}
        for view in VIEWS:
            screen = self.tela(('view', view), True)
            achado = VALOR.findall(self.tudo(screen))
            if achado:
                vazadas[view] = achado
        self.assertEqual({}, vazadas)

    def test_com_ocultar_desligado_os_valores_continuam_aparecendo(self):
        for view in ('pay', 'history', 'closing', 'categories', 'budgets', 'month_actions', 'balance'):
            screen = self.tela(('view', view), False)
            self.assertRegex(self.tudo(screen), VALOR, view)

    def test_a_pagar_e_detalhe_da_obrigacao(self):
        screen = self.tela(('view', 'pay'), True)
        self.assertIn('••••', screen.text)
        code = next(a for row in screen.rows for _, a in row if a[0] == 'detail_obligation')
        detalhe = self.engine.act(self.key, code)
        self.assertNotRegex(self.tudo(detalhe), VALOR)

    def test_historico_detalhe_do_lancamento(self):
        self.tela(('view', 'history'), True)
        tid = db.listar_transacoes_mes('2026-09')[0]['id'] if hasattr(db, 'listar_transacoes_mes') else None
        if tid is None:
            tid = dict(db.buscar_transacoes_por_mes('2026-09')[0])['id']
        screen = self.engine.act(self.key, ('transaction', tid))
        self.assertNotRegex(self.tudo(screen), VALOR)

    def test_quanto_vou_pagar_resumo_conta_e_detalhe(self):
        s = self.engine.session(self.key)
        s.privacy = True
        for acao in (('pay_month', '2026-09'), ('pay_month_expand', 'Itaú', '2026-09', 0),
                     ('pay_account', 'Itaú', '2026-09'), ('pay_account_detail', 'Itaú', '2026-09'),
                     ('pay_month_account_detail', 'Itaú', '2026-09')):
            screen = self.engine.act(self.key, acao)
            self.assertNotRegex(self.tudo(screen), VALOR, acao)
        s.privacy = False
        self.assertRegex(self.tudo(self.engine.act(self.key, ('pay_month', '2026-09'))), VALOR)

    def test_saldos_por_conta_e_detalhes(self):
        s = self.engine.session(self.key)
        s.privacy = True
        for acao in (('cash_accounts', '2026-09'), ('cash_account_detail', 'Itaú', '2026-09'),
                     ('balance_account', 'Itaú', '2026-09')):
            screen = self.engine.act(self.key, acao)
            self.assertNotRegex(self.tudo(screen), VALOR, acao)
        s.privacy = False
        self.assertRegex(self.tudo(self.engine.act(self.key, ('cash_accounts', '2026-09'))), VALOR)

    def test_botao_com_valor_no_rotulo_e_mascarado(self):
        screen = ux.Screen('<b>Teste</b>', [[('Energia · 210,00', ('view', 'pay')), ('Itaú · R$ 5,00', ('view', 'home'))]])
        s = self.engine.session(self.key)
        s.privacy = True
        self.engine._apply_privacy(s, screen)
        self.assertEqual(['Energia · ••••', 'Itaú · ••••'], [label for label, _ in screen.rows[0]])

    def test_consulta_em_texto_respeita_ocultar(self):
        s = self.engine.session(self.key)
        s.privacy = True
        screen = self.engine.fast_deterministic_query(self.key, 'quanto vou pagar')
        self.assertIsNotNone(screen)
        self.assertNotRegex(self.tudo(screen), VALOR)


class FormatoNasTelasTests(TelasBase):
    def test_vencimento_com_chip_e_plural(self):
        screen = self.tela(('view', 'pay'), False)
        self.assertIn('🔴 Vencido há 5 dias', screen.text)
        self.assertNotIn('(s)', screen.text)
        self.assertNotIn('(ns)', screen.text)

    def test_due_label_singular_e_futuro(self):
        item = lambda d: {'data': d}
        self.assertIn('🔴 Vencido há 1 dia ·', self.engine.due_label(item('2026-09-29')))
        self.assertIn('🟡 Vence hoje', self.engine.due_label(item('2026-09-30')))
        self.assertIn('🟡 Vence amanhã', self.engine.due_label(item('2026-10-01')))
        self.assertIn('⚪ Vence em 5 dias', self.engine.due_label(item('2026-10-05')))

    def test_nenhum_parenteses_de_plural_nas_telas(self):
        for view in VIEWS:
            texto = self.tela(('view', view), False).text
            self.assertNotRegex(texto, r'\w\((?:s|ns|ões)\)', view)

    def test_percentual_com_virgula_no_fechamento_e_analises(self):
        db.inserir_transacao(dict(data='2026-08-03', tipo='despesa', valor=100, categoria='Mercado',
                                  descricao='Agosto', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        for view in ('closing_details', 'analytics'):
            texto = self.tela(('view', view), False).text
            self.assertNotRegex(texto, r'\d\.\d%', view)
            self.assertRegex(texto, r'\d,\d%', view)

    def test_negativo_usa_menos_tipografico_nas_telas(self):
        db.inserir_transacao(dict(data='2026-09-20', tipo='despesa', valor=30000, categoria='Lazer',
                                  descricao='Viagem', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        texto = self.tudo(self.tela(('view', 'home'), False))
        self.assertNotIn('R$ -', texto)


class RotulosEspecificosTests(TelasBase):
    def rotulos(self, screen):
        return [label for row in screen.rows for label, _ in row]

    def test_atencao_diz_o_que_abre(self):
        screen = self.tela(('view', 'attention'), False)
        rotulos = self.rotulos(screen)
        self.assertFalse(any('Resolver / conferir' in r for r in rotulos), rotulos)
        self.assertTrue(any(re.match(r'Ver \d+ vencidas?', r) for r in rotulos), rotulos)

    def test_botoes_de_lista_nao_se_repetem(self):
        for view in ('categories', 'agenda', 'plan', 'attention'):
            rotulos = [r for r in self.rotulos(self.tela(('view', view), False))]
            itens = [r for r in rotulos if r.startswith(('Ver ', 'Abrir:')) or '·' in r]
            self.assertEqual(len(itens), len(set(itens)), (view, itens))
        self.assertFalse(any('Ver lançamentos' == r[2:] or r.endswith('. Ver lançamentos')
                             for r in self.rotulos(self.tela(('view', 'categories'), False))))

    def test_rotulos_cabem_no_limite_do_callback(self):
        for view in VIEWS:
            screen = self.tela(('view', view), False)
            for row in self.engine.tokens_for(self.key, screen):
                for _, token in row:
                    if token:
                        self.assertLessEqual(len(token.encode()), 64)


if __name__ == '__main__':
    unittest.main()
