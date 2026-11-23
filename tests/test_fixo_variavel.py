"""Fixo de valor variável (conta de luz) — pedido do titular em 18/11/2026.

Cenário de exemplo: a luz foi lançada como gasto comum de junho a outubro
(75,39 · 78,70 · 70,65 · 98,88 · 75,75); em novembro vira fixo variável com esse
histórico. Previsão = média dos 3 últimos meses pagos; a baixa pergunta o valor
real e fecha o mês com qualquer valor; a baixa seguinte entra na média.
Caminho real (``dispatch_text`` + ações dos botões) em banco temporário com migrations.
"""

import compromissos
import database as db
import fixos_variaveis as fv
import fixos_variaveis_acoes as fva
import services as svc
from tests.relogio_fixo import data_fixa
from tests.test_jornadas_ponta_a_ponta import JornadaBase, setUpModule, tearDownModule  # noqa: F401

LUZ = [('2026-06-25', 75.39, 'Luz', 'Mercado Pago'), ('2026-07-24', 78.70, 'Conta de luz', 'Itaú'),
       ('2026-08-25', 70.65, 'Conta de luz', 'Itaú'), ('2026-09-27', 98.88, 'Conta de Luz', 'Mercado Pago'),
       ('2026-10-26', 75.75, 'Luz', 'Mercado Pago')]


class RegrasPurasTests(JornadaBase):
    def test_media_dos_tres_ultimos_meses_antes_do_mes(self):
        hist = {'2026-08': 7065, '2026-09': 9888, '2026-10': 7575, '2026-07': 7870}
        self.assertEqual((81.76, ['2026-08', '2026-09', '2026-10']), fv.estimativa(hist, {}, '2026-11', 80))
        # A baixa de novembro entra; agosto sai da janela.
        self.assertEqual((87.31, ['2026-09', '2026-10', '2026-11']), fv.estimativa(hist, {'2026-11': 8730}, '2026-12', 80))
        self.assertEqual((80.0, []), fv.estimativa({}, {}, '2026-11', 80))

    def test_termos_e_elegibilidade(self):
        self.assertEqual(['luz'], fv.termos_busca('Conta de luz'))
        self.assertEqual(['agua', 'sabesp'], fv.termos_busca('Água Sabesp'))
        self.assertIsNone(fv.elegivel({'tipo': 'fixo', 'forma_pagamento': 'pix'}))
        self.assertIn('crédito', fv.elegivel({'tipo': 'fixo', 'forma_pagamento': 'crédito'}))
        self.assertIsNotNone(fv.elegivel({'tipo': 'parcelamento', 'forma_pagamento': 'pix'}))


class FixoVariavelLuzTests(JornadaBase):
    def setUp(self):
        super().setUp()
        self.luz_ids = [db.inserir_transacao(dict(data=d, tipo='despesa', valor=v, categoria='Moradia', descricao=n,
                                                  conta=c, forma_pagamento='pix', parcelas_total=1))
                        for d, v, n, c in LUZ]
        self.outro = db.inserir_transacao(dict(data='2026-10-02', tipo='despesa', valor=300, categoria='Mercado',
                                               descricao='Mercado Luzia', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        self.fixo = db.inserir_compromisso(dict(tipo='fixo', nome='Conta de luz', categoria='Moradia', valor=80,
                                                data_inicio='2026-11-01', dia_vencimento=25, conta_pagamento='Itaú',
                                                forma_pagamento='pix', ativo=True))

    def item_mes(self, mes):
        return next(i for i in compromissos.projetar_pagamentos_mes(mes, incluir_transacoes=False)
                    if i.get('origem') == 'compromisso' and i['id'] == self.fixo)

    def ativar_pela_tela(self):
        tela = self.agir(('fixed_detail', self.fixo))
        self.assertIn(('fixed_var', self.fixo), self.acoes())
        tela = self.clicar('fixed_var', self.fixo)
        self.assertIn('Encontrei 5 lançamento(s)', tela.text)  # "Mercado Luzia" não é "luz"
        self.assertIn('≈ R$ 81,76', tela.text)
        self.assertEqual(80, dict(db.buscar_compromisso_por_id(self.fixo))['valor'])  # prévia não grava
        self.assertFalse(fva.eh_variavel(self.fixo))
        return self.clicar('fixed_var_ok', self.fixo)

    def baixar_com_valor(self, valor, conta='Itaú', mes='2026-11'):
        self.agir(('settle', self.fixo, mes))
        self.assertEqual('amount', self.estagio(), 'fixo variável: a baixa pergunta o valor primeiro')
        self.dizer(valor)
        self.assertEqual('account', self.estagio())
        self.clicar('answer', conta)
        return self.clicar('commit')

    def test_jornada_completa_luz(self):
        tela = self.ativar_pela_tela()
        self.assertIn('agora tem valor variável', tela.text)
        self.assertTrue(fva.eh_variavel(self.fixo))
        # Lançamentos antigos intactos (só entram na média).
        self.assertEqual([75.39, 78.70, 70.65, 98.88, 75.75],
                         [dict(db.buscar_transacao_por_id(i))['valor'] for i in self.luz_ids])
        # Previsão de novembro = média ago/set/out.
        item = self.item_mes('2026-11')
        self.assertEqual(81.76, item['valor'])
        self.assertTrue(item['valor_estimado'])
        a_pagar = self.agir(('view', 'pay'))
        self.assertIn('Conta de luz · ≈ R$ 81,76', a_pagar.text)

        # Baixa de novembro com o valor real (maior que a estimativa: não é recusada).
        self.baixar_com_valor('92,10')
        nov = self.item_mes('2026-11')
        self.assertEqual(0.0, nov['valor'])
        self.assertTrue(nov['conciliado'])
        self.assertEqual(92.10, nov['valor_conciliado'])
        abertos = [i for i in self.engine._pay_month_open_items('2026-11') if i.get('id') == self.fixo]
        self.assertEqual([], abertos, 'baixa de qualquer valor fecha o mês (sem resto)')
        # Dezembro: média de set (98,88), out (75,75) e nov (92,10) = 266,73 / 3 = 88,91.
        self.assertEqual(88.91, self.item_mes('2026-12')['valor'])

    def test_baixa_menor_nao_deixa_resto_e_segunda_baixa_e_recusada(self):
        self.ativar_pela_tela()
        self.baixar_com_valor('60,00')
        self.assertEqual(0.0, self.item_mes('2026-11')['valor'])
        tela = self.agir(('settle', self.fixo, '2026-11'))
        self.assertIn('já está conciliada', tela.text)

    def test_saldo_previsto_usa_a_estimativa(self):
        antes = svc.obter_metricas_resultado_mes('2026-11')
        self.ativar_pela_tela()
        depois = svc.obter_metricas_resultado_mes('2026-11')
        # A previsão de despesas troca 80 (cadastro) por 81,76 (estimativa).
        self.assertAlmostEqual(1.76, antes['saldo_projetado'] - depois['saldo_projetado'], places=2)

    def test_sem_historico_usa_o_cadastro_e_desligar_volta_ao_fixo(self):
        self.agir(('fixed_var', self.fixo))
        self.assertIn(('fixed_var_ok', self.fixo, '-'), self.acoes())
        self.agir(('fixed_var_ok', self.fixo, '-'))
        self.assertEqual(80.0, self.item_mes('2026-11')['valor'])
        self.agir(('fixed_var', self.fixo))
        self.clicar('fixed_var_off', self.fixo)
        self.clicar('fixed_var_off_ok', self.fixo)
        self.assertFalse(fva.eh_variavel(self.fixo))
        self.assertNotIn('valor_estimado', self.item_mes('2026-11'))

    def test_previa_desatualizada_nao_ativa(self):
        self.agir(('fixed_var', self.fixo))
        acao = next(a for a in self.acoes() if a[0] == 'fixed_var_ok' and a[2] != '-')
        db.inserir_transacao(dict(data='2026-10-15', tipo='despesa', valor=10, categoria='Moradia', descricao='luz extra',
                                  conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        with data_fixa(self.HOJE):
            tela = self.agir(acao)
        self.assertIn('mudaram desde a prévia', tela.text)
        self.assertFalse(fva.eh_variavel(self.fixo))

    def test_fixo_no_credito_nao_pode_ser_variavel(self):
        cartao = db.inserir_compromisso(dict(tipo='fixo', nome='Streaming luz', categoria='Assinaturas', valor=30,
                                             data_inicio='2026-11-01', dia_vencimento=10, conta_pagamento='Nubank',
                                             forma_pagamento='crédito', ativo=True))
        tela = self.agir(('fixed_var', cartao))
        self.assertIn('pago no crédito', tela.text)
        self.assertFalse(any(a[0] == 'fixed_var_ok' for a in self.acoes()))

    def test_fixo_comum_continua_igual(self):
        # Sem marcar variável: baixa sem pergunta de valor e valor maior segue recusado na conciliação.
        self.agir(('settle', self.fixo, '2026-11'))
        self.assertEqual('account', self.estagio())
        item = self.item_mes('2026-11')
        self.assertEqual(80, item['valor'])
        self.assertNotIn('valor_estimado', item)
