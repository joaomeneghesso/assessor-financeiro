"""Telas de fixos: milhar, datas em DD/MM/AAAA, sem ids/ISO no corpo, acentos e rodapé padrão."""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import fixos_edicao as fx
import fixos_interface as ui
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 11, 9)


class Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 9)


def corpo(tela):
    """Texto principal sem a linha discreta de código (itálico)."""
    return '\n'.join(l for l in tela.text.split('\n') if not l.startswith('<i>'))


class FixosIdentidadeVisual(unittest.TestCase):
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

    def telas(self):
        telas = [ui.listar(self.exp, 'k'), ui.detalhe(self.exp, 'k', self.ident),
                 ui.campos(self.exp, 'k', self.ident)]
        ui.acao(self.exp, 'k', ('fixed_field', self.ident, 'valor'))
        telas.append(ui.retomar(self.exp, 'k'))
        ui.texto(self.exp, 'k', '1600')
        telas.append(ui.acao(self.exp, 'k', ('fixed_scope', 'month')))
        telas.append(ui.texto(self.exp, 'k', 'dezembro'))
        return telas

    def test_milhar_e_data_br(self):
        texto = '\n'.join(t.text for t in self.telas())
        self.assertIn('R$ 1.500,00', texto)
        self.assertIn('R$ 1.600,00', texto)
        self.assertIn('01/06/2026', texto)
        self.assertIn('30/11/2027', texto)
        self.assertIn('Novembro 2026', texto)
        self.assertNotRegex(texto, r'R\$ \d{4,}')

    def test_sem_iso_e_sem_id_no_corpo(self):
        for tela in self.telas():
            c = corpo(tela)
            self.assertNotRegex(c, r'\d{4}-\d{2}(-\d{2})?')
            self.assertNotIn('#C', c)
            self.assertNotIn('#F', c)
            self.assertNotRegex(c, r'\b[a-z]+_[a-z_]+\b')

    def test_codigo_para_comandos_em_linha_discreta(self):
        detalhe = ui.detalhe(self.exp, 'k', self.ident)
        self.assertTrue(detalhe.text.endswith(f'<i>Código para comandos de texto: #C{self.ident}</i>'))

    def test_acentos(self):
        for tela in self.telas():
            self.assertNotIn('Inicio', tela.text)
            self.assertNotIn('sugestao', tela.text)
            for linha in tela.rows:
                for rotulo, _ in linha:
                    self.assertNotIn('Inicio', rotulo)

    def test_rodape_padrao_e_acoes_validas(self):
        for tela in self.telas():
            ultima = tela.rows[-1]
            self.assertEqual(['↩ Voltar', '🏠 Início', '☰ Menu'], [r for r, _ in ultima])
            self.assertEqual([('view', 'home'), ('view', 'more')], [a for _, a in ultima[1:]])
            for linha in tela.rows:
                for rotulo, acao in linha:
                    self.assertNotIn('#C', rotulo)
                    self.assertLessEqual(len(':'.join(map(str, acao)).encode()), 64)

    def test_exibir_dinheiro_data_mes(self):
        self.assertEqual('R$ 1.500,00', fx.exibir('valor', 1500.0))
        self.assertEqual('R$ 1.234.567,89', fx.exibir('valor', 1234567.89))
        self.assertEqual('−R$ 1.234,56', fx.exibir('valor', -1234.56))
        self.assertEqual('01/06/2026', fx.exibir('inicio', '2026-06-01'))
        self.assertEqual('sem término', fx.exibir('termino', None))
        self.assertEqual('Novembro 2026', fx.mes_extenso('2026-11'))

    def test_resultado_do_salvar_sem_iso_e_com_dica(self):
        ui.acao(self.exp, 'k', ('fixed_field', self.ident, 'valor'))
        ui.texto(self.exp, 'k', '1600')
        ui.acao(self.exp, 'k', ('fixed_scope', 'month'))
        ui.texto(self.exp, 'k', 'dezembro')
        tela = ui.acao(self.exp, 'k', ('fixed_save',))
        c = corpo(tela)
        self.assertIn('Dezembro 2026', c)
        self.assertIn('30/11/2026', c)
        self.assertNotRegex(c, r'\d{4}-\d{2}')
        self.assertNotIn('#C', c)
        self.assertRegex(tela.text.split('\n')[-1], r'^<i>Código para comandos de texto: #C\d+</i>$')


if __name__ == '__main__':
    unittest.main()
