"""Fase 2 (B4/B5/B7): limites com barra/ritmo, "o que cresceu" por categoria e "Posso comprar?".

Banco temporário e data fixa; nada toca data/financeiro.db. Tudo é somente leitura.
"""
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import assessor_orientacao as orient
import database as db
import services as svc
import telegram_experiencia as ux
from saldo_resumo import resumir_saldo

HOJE = date(2026, 10, 20)
KEY = 'fase2'


class BaseFase2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        db.definir_saldo_inicial_conta_mes('2026-10', 'Itaú', 5000)
        self.engine = ux.Experience(date_provider=lambda: HOJE)

    def tx(self, dia, valor, categoria, tipo='despesa', desc=None):
        return db.inserir_transacao(dict(data=dia, tipo=tipo, valor=valor, categoria=categoria,
                                         descricao=desc or categoria, conta='Itaú', forma_pagamento='pix'))

    def financeiro(self):
        with db.get_connection() as c:
            return {t: [tuple(r) for r in c.execute('SELECT * FROM ' + t)]
                    for t in ('transacoes', 'compromissos', 'fatura_movimentos', 'saldos_mensais_contas', 'metas')}


class BarraETextoTests(unittest.TestCase):
    def test_barra_tem_largura_fixa_e_satura(self):
        self.assertEqual('▱' * 10, orient.barra(0))
        self.assertEqual('▰' * 5 + '▱' * 5, orient.barra(0.5))
        self.assertEqual('▰' * 10, orient.barra(5.9))
        self.assertEqual('▰▱▱▱▱▱▱▱▱▱', orient.barra(0.01))  # >0% sempre mostra um bloco

    def test_extrai_total_parcelas_e_descricao(self):
        p = orient.extrair_pergunta_compra('posso comprar um celular de 3000 em 10x')
        self.assertEqual((300000, 10, 'celular', True), (p['total_centavos'], p['parcelas'], p['descricao'], p['credito']))
        p = orient.extrair_pergunta_compra('posso comprar um drone em 10x de 300 reais?')
        self.assertEqual((300000, 10), (p['total_centavos'], p['parcelas']))
        p = orient.extrair_pergunta_compra('vale a pena comprar um tênis de R$ 1.299,90 no pix')
        self.assertEqual((129990, 1, False), (p['total_centavos'], p['parcelas'], p['credito']))
        self.assertIsNone(orient.extrair_pergunta_compra('posso comprar um celular?'))
        self.assertTrue(orient.eh_pergunta_compra('Posso comprar um carro?'))
        self.assertFalse(orient.eh_pergunta_compra('comprei um carro'))


class LimitesTests(BaseFase2):
    def setUp(self):
        super().setUp()
        for dia, v in (('2026-10-03', 300), ('2026-10-08', 200), ('2026-10-12', 150)):
            self.tx(dia, v, 'Mercado')
        self.tx('2026-10-10', 1900, 'Lazer', desc='Viagem')
        self.tx('2026-10-11', 25, 'Casa')
        db.definir_meta('Mercado', 800)
        db.definir_meta('Lazer', 400)
        db.definir_meta('Casa', 100)

    def itens(self):
        metas = db.listar_metas()
        txs = [dict(t) for t in db.buscar_transacoes_por_competencia('2026-10')]
        return {i['categoria']: i for i in orient.situacao_limites(metas, txs, HOJE, '2026-10')}

    def test_ritmo_margem_diaria_e_estados(self):
        i = self.itens()
        mercado = i['Mercado']
        self.assertEqual(Decimal('650.00'), mercado['gasto'])
        self.assertEqual(Decimal('516.13'), mercado['esperado'])      # 800 * 20/31
        self.assertEqual(Decimal('1007.50'), mercado['ritmo'])         # 650/20*31
        self.assertEqual(Decimal('12.50'), mercado['por_dia'])         # 150 / 12 dias restantes (inclui hoje)
        self.assertEqual('ritmo', mercado['estado'])
        self.assertEqual('estourou', i['Lazer']['estado'])
        self.assertEqual('ok', i['Casa']['estado'])
        self.assertIsNone(i['Casa']['ritmo'])                          # 1 lançamento: sem base para ritmo

    def test_estouro_por_um_lancamento_e_identificado(self):
        evento = self.itens()['Lazer']['evento']
        self.assertEqual((Decimal('1900.00'), 'Viagem', 1), evento)

    def test_sem_dias_suficientes_nao_projeta_ritmo(self):
        metas = db.listar_metas()
        txs = [dict(t) for t in db.buscar_transacoes_por_competencia('2026-10')]
        r = {i['categoria']: i for i in orient.situacao_limites(metas, txs, date(2026, 10, 4), '2026-10')}
        self.assertIsNone(r['Mercado']['ritmo'])

    def test_tela_mostra_barra_ritmo_e_margem(self):
        antes = self.financeiro()
        t = self.engine.act(KEY, ('view', 'budgets')).text
        self.assertIn('▰', t)
        self.assertIn('🔴', t)
        self.assertIn('🟡', t)
        self.assertIn('/dia até o fim do mês', t)
        self.assertIn('no ritmo atual fecha em', t)
        self.assertIn('Um único lançamento de R$ 1.900,00', t)
        self.assertLess(t.index('Lazer'), t.index('Mercado'))          # mais crítico primeiro
        self.assertEqual(antes, self.financeiro())

    def test_privacidade_oculta_valores_mas_mantem_barra_e_percentual(self):
        self.engine.act(KEY, ('privacy',))
        t = self.engine.act(KEY, ('view', 'budgets')).text
        self.assertNotIn('R$', t)
        self.assertIn('▰', t)
        self.assertIn('%', t)

    def test_limite_zero_e_ignorado(self):
        db.definir_meta('Outros', 0.0)
        self.assertNotIn('Outros', self.itens())


class OQueCresceuTests(BaseFase2):
    def setUp(self):
        super().setUp()
        self.tx('2026-09-05', 100, 'Mercado')
        self.tx('2026-09-10', 90, 'Lazer')
        self.tx('2026-09-28', 500, 'Mercado')       # fora da janela (dia 20): não pode contar
        self.tx('2026-10-05', 300, 'Mercado')
        self.tx('2026-10-08', 350, 'Mercado')
        self.tx('2026-10-10', 1900, 'Lazer', desc='Viagem')
        self.tx('2026-10-12', 40, 'Transporte')      # categoria sem base anterior

    def variacao(self):
        import dashboard_metricas as dm
        return dm.variacao_categorias(self.engine, '2026-10', HOJE)

    def test_top_por_categoria_com_mesma_janela(self):
        v = self.variacao()
        self.assertTrue(v['base'])
        self.assertEqual(20, v['day'])
        nomes = [l['categoria'] for l in v['subiram']]
        self.assertEqual(['Lazer', 'Mercado', 'Transporte'], nomes)
        lazer, mercado, transporte = v['subiram']
        self.assertEqual(Decimal('1810.00'), lazer['delta'])
        self.assertEqual(Decimal('550.00'), mercado['delta'])            # 650 − 100 (o dia 28 ficou de fora)
        self.assertAlmostEqual(550.0, mercado['percent'])
        self.assertIsNone(transporte['percent'])                        # sem base: não inventa %
        self.assertTrue(lazer['um_lancamento'])

    def test_sem_base_anterior_nao_fabrica_variacao(self):
        with db.get_connection() as c:
            c.execute("DELETE FROM transacoes WHERE data LIKE '2026-09-%'")
        v = self.variacao()
        self.assertFalse(v['base'])
        t = self.engine.act(KEY, ('view', 'analytics')).text
        self.assertIn('Sem base', t)
        self.assertNotIn('↑', t)

    def test_futuro_nao_tem_variacao(self):
        import dashboard_metricas as dm
        self.assertIsNone(dm.variacao_categorias(self.engine, '2026-11', HOJE))

    def test_analises_e_fechamento_mostram_e_privacidade_mascara(self):
        antes = self.financeiro()
        for view in ('analytics', 'closing'):
            t = self.engine.act(KEY, ('view', view)).text
            self.assertIn('O que cresceu vs. Setembro 2026', t, view)
            self.assertIn('↑ <b>Lazer</b> · +R$ 1.810,00', t, view)
        self.assertEqual(antes, self.financeiro())
        self.engine.act(KEY, ('privacy',))
        for view in ('analytics', 'closing'):
            t = self.engine.act(KEY, ('view', view)).text
            self.assertNotIn('R$', t, view)
            self.assertIn('+2011,1%', t, view)


class PossoComprarTests(BaseFase2):
    def setUp(self):
        super().setUp()
        self.tx('2026-10-02', 4000, 'Salário', tipo='receita')
        self.tx('2026-10-05', 300, 'Mercado')
        db.inserir_compromisso(dict(tipo='fixo', nome='Aluguel', categoria='Casa', valor=1000,
                                    data_inicio='2026-10-01', dia_vencimento=28, conta_pagamento='Itaú',
                                    forma_pagamento='pix', ativo=1))

    def final(self, mes='2026-10'):
        return resumir_saldo(svc.obter_metricas_resultado_mes(mes))['saldo_final']

    def test_texto_livre_usa_o_motor_canonico_e_bate_com_o_inicio(self):
        antes_banco = self.financeiro()
        sobra = self.final()
        t = self.engine.handle_text(KEY, 'posso comprar um celular de 3000 em 10x').text
        self.assertIn('Posso comprar?', t)
        self.assertIn('Nada será gravado', t)
        self.assertIn(f'Antes da compra: <b>{ux.money(sobra)}</b>', t)
        self.assertIn(f'Depois da compra: <b>{ux.money(sobra - 300)}</b>', t)   # depois = antes − parcela
        self.assertIn('10x de R$ 300,00', t)
        self.assertIn('Mês mais apertado', t)
        self.assertNotIn('Saldo atual', t)                                      # fórmula legada
        inicio = self.engine.act(KEY, ('view', 'home')).text
        self.assertIn(ux.money(sobra), inicio)                                  # mesmo número do Início
        self.assertEqual(antes_banco, self.financeiro())                        # simulação não persiste

    def test_veredito_e_descritivo_nunca_prescritivo(self):
        for pergunta in ('posso comprar um celular de 3000 em 10x', 'posso comprar um carro de 900000 em 10x',
                         'posso comprar um tênis de 100 no pix'):
            t = self.engine.handle_text(KEY, pergunta).text
            self.assertIn('Leitura:', t)
            self.assertIn('não uma recomendação', t)
            minusculo = t.lower()
            for proibido in ('compre', 'você deve comprar', 'recomendo', 'invista'):
                self.assertNotIn(proibido, minusculo)

    def test_compra_que_deixa_o_mes_negativo_gera_aviso(self):
        t = self.engine.handle_text(KEY, 'posso comprar um carro de 900000 no pix').text
        self.assertIn('🔴', t)
        self.assertIn('fecha com −R$', t)

    def test_compra_pequena_cabe(self):
        t = self.engine.handle_text(KEY, 'posso comprar um livro de 50 no pix').text
        self.assertIn('🟢', t)
        self.assertIn('continua positiva', t)

    def test_parcela_pesada_aperta(self):
        sobra = self.final()
        valor = int(Decimal(str(sobra)) * Decimal('0.6'))
        t = self.engine.handle_text(KEY, f'posso comprar um sofá de {valor} no pix').text
        self.assertIn('🟡', t)
        self.assertIn('consome 60%', t)

    def test_sem_valor_pede_o_valor_sem_cair_no_legado(self):
        s = self.engine.handle_text(KEY, 'posso comprar um celular?')
        self.assertIn('Preciso do valor', s.text)
        self.assertNotIn('Saldo atual', s.text)

    def test_botoes_de_variacao_recalculam_sem_gravar(self):
        self.engine.handle_text(KEY, 'posso comprar um celular de 3000 em 10x')
        antes = self.financeiro()
        t3 = self.engine.act(KEY, ('buy_sim', 3)).text
        self.assertIn('3x de R$ 1.000,00', t3)
        t1 = self.engine.act(KEY, ('buy_sim', 1)).text
        self.assertIn('à vista', t1)
        self.assertIn(f'Depois da compra: <b>{ux.money(self.final() - 3000)}</b>', t1)
        self.assertEqual(antes, self.financeiro())
        with self.assertRaises(ValueError):
            ux.Experience(date_provider=lambda: HOJE).act('outra', ('buy_sim', 3))

    def test_privacidade_mascara_valores(self):
        self.engine.act(KEY, ('privacy',))
        t = self.engine.handle_text(KEY, 'posso comprar um celular de 3000 em 10x').text
        self.assertNotIn('R$', t)
        self.assertIn('Deve sobrar', t)

    def test_credito_apos_o_corte_oferece_escolha_de_fatura(self):
        eng = ux.Experience(date_provider=lambda: date(2026, 10, 27))
        t = eng.handle_text(KEY, 'posso comprar um celular de 3000 em 10x')
        self.assertIn('fatura de Novembro 2026', t.text)
        self.assertTrue(any(a == ('buy_fatura',) for row in t.rows for _, a in row))
        t2 = eng.act(KEY, ('buy_fatura',))
        self.assertIn('fatura de Outubro 2026', t2.text)

    def test_simulacao_guiada_tambem_mostra_antes_e_depois(self):
        sobra = self.final()
        t = self.engine.handle_text(KEY, 'simular comprei celular 3000 reais no pix conta Itaú').text
        self.assertIn('Antes da compra', t)
        self.assertIn(f'Depois da compra: <b>{ux.money(sobra - 3000)}</b>', t)


if __name__ == '__main__':
    unittest.main()
