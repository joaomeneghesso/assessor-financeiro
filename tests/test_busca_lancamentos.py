"""Busca em todos os meses e troca de categoria em lote (pedido do titular em 13/11/2026).

Antes: "buscar bruno" abria o Histórico só do mês atual (1 de 3 lançamentos do
"Bar Bruno C") e não havia como mudar a categoria de vários de uma vez.
Agora: a busca olha todos os meses (ou o período pedido), mostra total e
categorias, e "Mudar categoria de todos" abre prévia antes → depois; só grava ao
confirmar, falha fechado se algo mudou e oferece aprender a regra.
"""
import os
import sqlite3
from contextlib import closing
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import busca_lancamentos as busca
import categorias_pessoais
import database as db
import services as svc
import telegram_experiencia as ux
from tests.test_jornadas_ponta_a_ponta import JornadaBase, setUpModule, tearDownModule  # noqa: F401

HOJE = date(2026, 11, 13)


def acoes(tela):
    return [tuple(a) for linha in tela.rows for _, a in linha]


class InterpretarBuscaTests(unittest.TestCase):
    def test_sem_periodo_e_todos_os_meses(self):
        self.assertEqual(('bruno', ''), busca.interpretar_busca('bruno', HOJE))
        self.assertEqual(('Bar Bruno C', ''), busca.interpretar_busca('Bar Bruno C', HOJE))
        self.assertEqual(('92,50', ''), busca.interpretar_busca('92,50', HOJE))

    def test_com_periodo(self):
        self.assertEqual(('bruno', '2026-09:2026-11'), busca.interpretar_busca('bruno nos últimos 3 meses', HOJE))
        self.assertEqual(('bruno', '2026-07:2026-11'), busca.interpretar_busca('bruno de julho a novembro', HOJE))
        self.assertEqual(('bruno', '2025-01:2025-12'), busca.interpretar_busca('bruno em 2025', HOJE))
        self.assertEqual(('bruno', '2026-10:2026-10'), busca.interpretar_busca('bruno mês passado', HOJE))
        self.assertEqual(('', '2026-06:2026-06'), busca.interpretar_busca('2026-06', HOJE))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.banco = Path(self.tmp.name) / 'fixture.db'
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', self.banco)
            p.start()
            self.addCleanup(p.stop)
        p = patch.dict(os.environ, {'ASSESSOR_CATEGORY_RULES_PATH': str(Path(self.tmp.name) / 'regras.json')})
        p.start()
        self.addCleanup(p.stop)
        db.init_db()
        self.ids = [self.tx(d, 50, 'Bar Bruno C') for d in ('2026-08-02', '2026-10-05', '2026-11-03')]
        self.outro = self.tx('2026-11-04', 30, 'Padaria')
        self.receita = self.tx('2026-11-05', 200, 'Reembolso Bruno', tipo='receita', categoria='Receita')
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = 'teste-busca'

    def tx(self, data, valor, desc, tipo='despesa', categoria='Alimentação'):
        return db.inserir_transacao(dict(data=data, tipo=tipo, valor=valor, categoria=categoria, descricao=desc,
                                         conta='Itaú', forma_pagamento='pix', parcelas_total=1))

    def categorias(self):
        with closing(sqlite3.connect(self.banco)) as c:
            return dict(c.execute('SELECT id, categoria FROM transacoes'))

    def valores(self):
        with closing(sqlite3.connect(self.banco)) as c:
            return c.execute('SELECT id, data, valor, conta, forma_pagamento FROM transacoes ORDER BY id').fetchall()


class BuscaEmTodosOsMesesTests(Base):
    def test_buscar_acha_todos_os_meses(self):
        tela = self.engine.handle_text(self.key, 'buscar bruno')
        self.assertIn('Todos os meses', tela.text)
        self.assertIn('4 lançamentos encontrados', tela.text)  # 3 do bar + o reembolso (entrada)
        self.assertIn('02/08/2026', tela.text)  # agosto aparece (antes: só novembro)
        self.assertIn('Saídas: <b>R$ 150,00</b>', tela.text)
        self.assertIn('Entradas: <b>R$ 200,00</b>', tela.text)
        self.assertNotIn('Padaria', tela.text)
        self.assertIn(('transaction', self.ids[0]), acoes(tela))
        self.assertIn(('busca_cat', 'bruno', '', 0), acoes(tela))
        self.assertEqual('bruno', self.engine.session(self.key).search)  # Histórico do mês segue com o filtro

    def test_buscar_com_periodo_e_sinonimos(self):
        for frase in ('procurar bruno nos últimos 2 meses', 'pesquisar bruno de outubro a novembro'):
            with self.subTest(frase=frase):
                tela = self.engine.handle_text(self.key, frase)
                self.assertIn('Outubro 2026 a Novembro 2026', tela.text)
                self.assertNotIn('02/08/2026', tela.text)

    def test_nada_encontrado(self):
        tela = self.engine.handle_text(self.key, 'buscar xpto inexistente')
        self.assertIn('Nenhum lançamento encontrado', tela.text)

    def test_paginacao(self):
        for i in range(10):
            self.tx(f'2026-09-{i + 1:02d}', 10, f'Bruno extra {i}')
        tela = self.engine.handle_text(self.key, 'buscar bruno')
        self.assertIn('Página 1/2', tela.text)
        tela = self.engine.act(self.key, ('busca', 'bruno', '', 1))
        self.assertIn('Página 2/2', tela.text)


class TrocaDeCategoriaEmLoteTests(Base):
    def previa(self, categoria='Lazer', termo='bruno', periodo=''):
        tela = self.engine.act(self.key, ('busca_cat_ver', termo, periodo, categoria))
        confirmar = next(a for a in acoes(tela) if a[0] == 'busca_cat_ok')
        return tela, confirmar

    def test_previa_nao_grava_e_confirmar_grava_so_as_saidas(self):
        antes_valores = self.valores()
        tela = self.engine.act(self.key, ('busca_cat', 'bruno', '', 0))
        self.assertIn(('busca_cat_ver', 'bruno', '', 'Lazer'), acoes(tela))
        tela, confirmar = self.previa()
        self.assertIn('3 lançamentos mudam para <b>Lazer</b>', tela.text)
        self.assertIn('Alimentação → Lazer', tela.text)
        self.assertNotIn('Reembolso', tela.text)
        self.assertEqual('Alimentação', self.categorias()[self.ids[0]])  # prévia não grava
        tela = self.engine.act(self.key, confirmar)
        self.assertIn('3 lançamentos agora estão em <b>Lazer</b>', tela.text)
        cats = self.categorias()
        self.assertEqual(['Lazer'] * 3, [cats[i] for i in self.ids])
        self.assertEqual('Receita', cats[self.receita])
        self.assertEqual('Alimentação', cats[self.outro])
        self.assertEqual(antes_valores, self.valores())  # valor, data, conta e forma intactos
        with closing(sqlite3.connect(self.banco)) as c:
            n = c.execute("SELECT COUNT(*) FROM auditoria_eventos WHERE operacao='categoria_alterada_lote'").fetchone()[0]
        self.assertEqual(3, n)

    def test_toque_duplo_nao_grava_de_novo(self):
        _, confirmar = self.previa()
        self.engine.act(self.key, confirmar)
        tela = self.engine.act(self.key, confirmar)
        self.assertIn('não vale mais', tela.text)

    def test_previa_desatualizada_nao_grava_nada(self):
        _, confirmar = self.previa()
        db.atualizar_categoria_por_id(self.ids[1], 'Mercado')  # mudou depois da prévia
        tela = self.engine.act(self.key, confirmar)
        self.assertIn('Nada foi alterado', tela.text)
        cats = self.categorias()
        self.assertEqual(['Alimentação', 'Mercado', 'Alimentação'], [cats[i] for i in self.ids])

    def test_periodo_limita_a_troca(self):
        _, confirmar = self.previa(periodo='2026-10:2026-11')
        self.engine.act(self.key, confirmar)
        cats = self.categorias()
        self.assertEqual(['Alimentação', 'Lazer', 'Lazer'], [cats[i] for i in self.ids])

    def test_ja_na_categoria_nao_tem_o_que_alterar(self):
        tela = self.engine.act(self.key, ('busca_cat_ver', 'padaria', '', 'Alimentação'))
        self.assertIn('Nada a alterar', tela.text)
        self.assertFalse(any(a[0] == 'busca_cat_ok' for a in acoes(tela)))

    def test_parcelamento_muda_inteiro(self):
        ids = db.inserir_parcelamento_atomico([
            dict(data=f'2026-{m:02d}-10', tipo='despesa', valor=100, categoria='Alimentação', descricao='Show Bruno',
                 conta='Nubank', forma_pagamento='crédito', parcela_atual=i, parcelas_total=3)
            for i, m in enumerate((9, 10, 11), 1)])
        tela, confirmar = self.previa(termo='show bruno', periodo='2026-11:2026-11')
        self.assertIn('Parcelamentos mudam inteiros', tela.text)
        self.engine.act(self.key, confirmar)
        cats = self.categorias()
        self.assertEqual(['Lazer'] * 3, [cats[i] for i in ids])

    def test_aprender_regra_para_os_proximos(self):
        _, confirmar = self.previa()
        tela = self.engine.act(self.key, confirmar)
        self.assertIn(('busca_regra', 'bruno', 'Lazer'), acoes(tela))
        tela = self.engine.act(self.key, ('busca_regra', 'bruno', 'Lazer'))
        self.assertIn('Preferência aprendida', tela.text)
        self.assertEqual('Lazer', categorias_pessoais.sugerir_categoria_pessoal('Bar Bruno C'))

    def test_privacidade_esconde_valores(self):
        self.engine.session(self.key).privacy = True
        tela = self.engine.handle_text(self.key, 'buscar bruno')
        self.assertNotIn('R$ 50,00', tela.text)


class BuscaPeloTelegramTests(JornadaBase):
    """Caminho real (dispatch_text) do texto até a gravação, por ação dos botões."""

    def test_buscar_e_mudar_categoria_de_todos(self):
        ids = [db.inserir_transacao(dict(data=d, tipo='despesa', valor=40, categoria='Alimentação', descricao='Bar Bruno C',
                                         conta='Itaú', forma_pagamento='pix', parcelas_total=1))
               for d in ('2026-08-02', '2026-11-03')]
        with patch.dict(os.environ, {'ASSESSOR_CATEGORY_RULES_PATH': str(Path(self.tmp.name) / 'regras.json')}):
            self.dizer('buscar bruno')
            self.assertIn('2 lançamentos encontrados', self.tela.text)
            self.clicar('busca_cat')
            self.assertIn(('busca_cat_ver', 'bruno', '', 'Lazer'), self.acoes())
            self.agir(('busca_cat_ver', 'bruno', '', 'Lazer'))
            self.clicar('busca_cat_ok')
        self.assertIn('agora estão em', self.tela.text)
        self.assertEqual(['Lazer', 'Lazer'], [dict(db.buscar_transacao_por_id(i))['categoria'] for i in ids])


if __name__ == '__main__':
    unittest.main()
