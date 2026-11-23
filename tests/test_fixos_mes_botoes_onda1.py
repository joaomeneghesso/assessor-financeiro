"""Onda 1: etapa 'A partir de qual mês?' com botões e texto livre; visual sem ISO nem milhar cru."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import fixos_interface as ui
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 11, 9)


class Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 9)


class InterpretarMes(unittest.TestCase):
    def test_formatos_validos(self):
        casos = {'2026-12': '2026-12', '12/2026': '2026-12', '1/2027': '2027-01', '11/26': '2026-11',
                 'novembro': '2026-11', 'janeiro': '2027-01', 'Novembro de 2026': '2026-11',
                 'nov': '2026-11', 'dezembro 2026': '2026-12', 'MARÇO': '2027-03', ' dez ': '2026-12',
                 'outubro': '2027-10', 'janeiro de 2028': '2028-01'}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(esperado, ui.interpretar_mes(texto, HOJE))

    def test_invalidos(self):
        for texto in ('13/2026', 'abc', '', '0/2026', '2026-13', 'ma', '12', 'mês que vem'):
            with self.subTest(texto=texto):
                self.assertIsNone(ui.interpretar_mes(texto, HOJE))

    def test_virada_de_ano(self):
        self.assertEqual('2027-01', ui.interpretar_mes('janeiro', date(2026, 12, 31)))
        self.assertEqual('2026-12', ui.interpretar_mes('dezembro', date(2026, 12, 31)))


class EtapaMesFixos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / 'fixture.db'
        for target, field, value in ((db, 'DB_PATH', path), (svc, 'DB_PATH', path),
                                     (comp, 'date', Hoje), (svc, 'date', Hoje)):
            p = patch.object(target, field, value)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.exp = ux.Experience(date_provider=lambda: HOJE)
        self.ident = db.inserir_compromisso(dict(
            tipo='fixo', nome='Aluguel', categoria='Moradia', conta_pagamento='Itaú',
            forma_pagamento='pix', valor=1500.0, dia_vencimento=10, data_inicio='2026-06-01',
            data_fim='2027-11-30', ativo=True, origem='teste_isolado'))

    def total(self):
        return len(db.listar_compromissos())

    def ate_etapa_mes(self):
        ui.acao(self.exp, 'k', ('fixed_field', self.ident, 'valor'))
        ui.texto(self.exp, 'k', '1600')
        return ui.acao(self.exp, 'k', ('fixed_scope', 'month'))

    def test_botoes_este_e_proximo_mes(self):
        tela = self.ate_etapa_mes()
        self.assertIn('digite o mês (ex.: 12/2026 ou dezembro)', tela.text)
        rotulos = [b[0] for row in tela.rows for b in row]
        self.assertIn('Este mês (Novembro 2026)', rotulos)
        self.assertIn('Próximo mês (Dezembro 2026)', rotulos)
        self.assertIn('Cancelar', rotulos)

    def test_botao_proximo_mes_chega_a_confirmacao_sem_gravar(self):
        tela = self.ate_etapa_mes()
        acao = next(b[1] for row in tela.rows for b in row if b[0].startswith('Próximo'))
        previa = ui.acao(self.exp, 'k', acao)
        self.assertIn('Confirmar edição', previa.text)
        self.assertIn('Dezembro 2026', previa.text)
        self.assertEqual(1, self.total())
        ui.acao(self.exp, 'k', ('fixed_save',))
        self.assertEqual(2, self.total())
        novo = max(db.listar_compromissos(tipo='fixo'), key=lambda c: c['id'])
        self.assertEqual('2026-12-01', novo['data_inicio'])

    def test_texto_equivale_a_aaaa_mm(self):
        referencia = None
        for texto in ('2026-12', 'dezembro', '12/2026', 'Dez 2026'):
            with self.subTest(texto=texto):
                self.ate_etapa_mes()
                previa = ui.texto(self.exp, 'k', texto)
                self.assertEqual('2026-12', self.exp.sessions['k'].fixed_edit['month'])
                self.assertEqual(1, self.total())
                if referencia is None:
                    referencia = previa.text
                self.assertEqual(referencia, previa.text)

    def test_texto_invalido_nao_avanca(self):
        self.ate_etapa_mes()
        with self.assertRaises(ValueError):
            ui.texto(self.exp, 'k', '13/2026')
        self.assertEqual('fixed_month', self.exp.sessions['k'].stage)
        self.assertEqual(1, self.total())

    def test_botao_so_vale_na_etapa_do_mes(self):
        ui.acao(self.exp, 'k', ('fixed_field', self.ident, 'valor'))
        with self.assertRaises(ValueError):
            ui.acao(self.exp, 'k', ('fixed_month_pick', '2026-12'))

    def test_visual_sem_milhar_cru_nem_data_iso(self):
        telas = [ui.detalhe(self.exp, 'k', self.ident), ui.campos(self.exp, 'k', self.ident),
                 ui.listar(self.exp, 'k')]
        ui.acao(self.exp, 'k', ('fixed_field', self.ident, 'valor'))
        ui.texto(self.exp, 'k', '1600')
        ui.acao(self.exp, 'k', ('fixed_scope', 'month'))
        telas.append(ui.texto(self.exp, 'k', 'dezembro'))
        texto = '\n'.join(t.text for t in telas)
        self.assertIn('R$ 1.500,00', texto)
        self.assertIn('R$ 1.600,00', texto)
        self.assertIn('01/06/2026', texto)
        self.assertIn('30/11/2027', texto)
        self.assertIn('Novembro 2026', texto)
        self.assertNotRegex(texto, r'R\$ \d{4,},')
        self.assertNotRegex(texto, r'\d{4}-\d{2}')


if __name__ == '__main__':
    unittest.main()
