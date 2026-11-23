"""Fase 2 do layout: rodapé de navegação unificado e A pagar em tabela rica.

Banco temporário; nada toca data/financeiro.db.
"""
import re
import unittest
from unittest.mock import patch

import database as db
import telegram_experiencia as ux
from tests.test_privacidade_formatacao_fase1 import TelasBase, VALOR

VIEWS_DE_MES = ('pay', 'balance', 'history', 'closing', 'analytics', 'budgets', 'agenda')


def acoes(screen):
    return [a for row in screen.rows for _, a in row]


def rotulos(screen):
    return [l for row in screen.rows for l, _ in row]


class RodapeTests(TelasBase):
    def abrir(self, view, trail=True):
        self.engine.sessions.pop(self.key, None)
        s = self.engine.session(self.key)
        s.trail = [('home', s.month, 0)] if trail else []
        return self.engine.act(self.key, ('view', view))

    def test_telas_de_mes_tem_linha_de_mes_e_uma_linha_voltar_inicio_menu(self):
        for view in VIEWS_DE_MES:
            screen = self.abrir(view)
            self.assertEqual(['‹ Mês', '📅 Período', 'Mês ›'], [l for l, _ in screen.rows[-2]], view)
            self.assertEqual(('month', -1, view), screen.rows[-2][0][1])
            self.assertEqual(('month', 1, view), screen.rows[-2][2][1])
            self.assertEqual(['↩ Voltar', '🏠 Início', '☰ Menu'], [l for l, _ in screen.rows[-1]], view)
            self.assertEqual(1, acoes(screen).count(('back',)), view)

    def test_sem_trilha_nao_ha_voltar(self):
        self.abrir('pay', trail=False)
        self.engine.session(self.key).trail = []
        screen = self.engine.render(self.key, 'pay')
        self.assertEqual(['🏠 Início', '☰ Menu'], [l for l, _ in screen.rows[-1]])
        self.assertNotIn(('back',), acoes(screen))

    def test_tela_sem_mes_so_tem_uma_linha_de_navegacao(self):
        screen = self.abrir('alerts')
        self.assertEqual(['↩ Voltar', '🏠 Início', '☰ Menu'], [l for l, _ in screen.rows[-1]])
        self.assertNotIn('📅 Período', rotulos(screen))

    def test_sem_voltar_duplicado_quando_ja_existe_voltar_explicito(self):
        s = self.engine.session(self.key)
        s.trail = [('analytics', s.month, 0)]
        screen = self.engine.act(self.key, ('category', 'Mercado'))
        voltares = [l for l in rotulos(screen) if 'Voltar' in l]
        self.assertLessEqual(len(voltares), 1, voltares)

    def test_rodape_de_mes_tem_duas_linhas(self):
        # Antes: Período|Menu, Início, Voltar = 3 linhas de rodapé. Agora 2.
        screen = self.abrir('pay')
        rodape = [r for r in screen.rows if any(a in {('view', 'home'), ('month', -1, 'pay'), ('back',)} for _, a in r)]
        self.assertEqual(2, len(rodape))

    def test_mes_avanca_direto_na_a_pagar(self):
        self.abrir('pay')
        antes = self.engine.session(self.key).month
        screen = self.engine.act(self.key, ('month', 1, 'pay'))
        self.assertNotEqual(antes, self.engine.session(self.key).month)
        self.assertIn('A pagar', screen.text)


class APagarRicaTests(TelasBase):
    def setUp(self):
        super().setUp()
        # HOJE = 2026-09-30: uma conta que vence hoje e uma futura.
        for nome, dia in (('Seguro', 30), ('Escola', 20)):
            db.inserir_compromisso(dict(tipo='fixo', nome=nome, categoria='Casa', valor=100,
                                        data_inicio='2026-09-01', dia_vencimento=dia,
                                        conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))

    def test_tabela_agrupada_por_urgencia_com_total_por_grupo(self):
        rich = self.tela(('view', 'pay'), False).rich_html
        self.assertIn('<table', rich)
        self.assertIn('🔴 Vencidas', rich)
        self.assertIn('Energia', rich)
        self.assertRegex(rich, r'<th[^>]*>Total 🔴</th>')
        self.assertLess(rich.index('🔴 Vencidas'), rich.index('Total 🔴'))

    def test_texto_e_botoes_por_item_continuam(self):
        screen = self.tela(('view', 'pay'), False)
        self.assertIn('Vencido há', screen.text)
        self.assertTrue(any(re.match(r'1\. ', l) for l in rotulos(screen)))
        self.assertIn('🔎 Filtrar', rotulos(screen))

    def test_com_ocultar_a_tabela_nao_mostra_valor(self):
        rich = self.tela(('view', 'pay'), True).rich_html
        self.assertNotRegex(rich, VALOR)
        self.assertIn('••••', rich)

    def test_fallback_pre_quando_tabela_falha(self):
        with patch.object(ux, 'rich_table', side_effect=ValueError('x')):
            screen = self.tela(('view', 'pay'), False)
        self.assertIn('<pre>', screen.rich_html)
        self.assertNotIn('<table', screen.rich_html)
        self.assertIn('Energia', screen.rich_html)

    def test_vazio_nao_quebra(self):
        self.engine.act(self.key, ('view', 'pay'))
        self.engine.session(self.key).month = '2020-01'
        screen = self.engine.render(self.key, 'pay')
        self.assertIn('<h2>', screen.rich_html)

    def test_respeita_limite_do_telegram(self):
        screen = self.tela(('view', 'pay'), False)
        self.assertLess(len(screen.rich_html), 4096)
        self.assertLess(len(screen.text), 4096)


if __name__ == '__main__':
    unittest.main()
