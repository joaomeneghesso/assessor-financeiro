"""'Quanto vou pagar de X' (faturas ou categoria) e Fixos por categoria — pedido de 19/11/2026.

Cenário de exemplo: Moradia = condomínio, IPTU, IPTV, internet e conta de luz
(valor variável); assinatura no crédito; compras no crédito em Itaú, Mercado Pago e
Infinitepay. Os totais têm de bater com a tela A pagar (mesma fonte).
"""
from datetime import date

import database as db
import fixos_variaveis_acoes as fva
from consultas_rapidas import interpretar_consulta, resolver_meses
from tests.test_jornadas_ponta_a_ponta import JornadaBase, setUpModule, tearDownModule  # noqa: F401


class InterpretarPagarTests(JornadaBase):
    def test_frases(self):
        for frase, cat in [('quanto vou pagar de moradia', 'moradia'), ('quanto vou pagar de cartão', 'cartao'),
                           ('quanto vou pagar de cartão de crédito', 'cartao de credito'),
                           ('quanto vou pagar de faturas', 'faturas'), ('quanto tenho que pagar de assinaturas', 'assinaturas'),
                           ('contas a pagar de moradia', 'moradia')]:
            with self.subTest(frase=frase):
                p = interpretar_consulta(frase)
                self.assertEqual(('payables_category', cat), (p['query_type'], p['category']))
        hoje = date(2026, 11, 19)
        self.assertEqual(['2027-01'], resolver_meses(interpretar_consulta('quanto vou pagar de moradia em janeiro'), hoje))
        self.assertEqual(['2026-11', '2026-12', '2027-01'],
                         resolver_meses(interpretar_consulta('quanto vou pagar de moradia nos próximos 3 meses'), hoje))
        self.assertIsNone(interpretar_consulta('quanto vou pagar'))  # segue para a tela A pagar de sempre
        self.assertIsNone(interpretar_consulta('quanto gastei no cartão'))  # gastos: comportamento antigo


class PagarPorCategoriaTests(JornadaBase):
    def setUp(self):
        super().setUp()
        self.ajustar_saldo('Itaú', '5000')
        f = lambda nome, valor, dia, forma='pix', conta='Itaú', cat='Moradia': db.inserir_compromisso(dict(
            tipo='fixo', nome=nome, categoria=cat, valor=valor, data_inicio='2026-06-01', dia_vencimento=dia,
            conta_pagamento=conta, forma_pagamento=forma, ativo=True))
        self.ids = {n: f(n, v, d) for n, v, d in [('Condominio', 600, 10), ('IPTU', 150, 15), ('IPTV', 50, 20),
                                                  ('Internet', 120, 22), ('Conta de luz', 80, 25)]}
        self.youtube = f('YouTube Premium', 24.9, 12, 'crédito', 'Nubank', 'Assinaturas')
        for d, v, n in [('2026-08-25', 70.65, 'Conta de luz'), ('2026-09-27', 98.88, 'Conta de Luz'), ('2026-10-26', 75.75, 'Luz')]:
            db.inserir_transacao(dict(data=d, tipo='despesa', valor=v, categoria='Moradia', descricao=n, conta='Itaú',
                                      forma_pagamento='pix', parcelas_total=1))
        luz = self.ids['Conta de luz']
        fva.ativar(luz, [t['id'] for t in fva.candidatos(db.buscar_compromisso_por_id(luz), '2026-11')])
        for conta, valor in [('Itaú', 300), ('Mercado Pago', 120.5), ('Infinitepay', 80)]:
            db.inserir_transacao(dict(data='2026-11-03', tipo='despesa', valor=valor, categoria='Mercado',
                                      descricao=f'Compra {conta}', conta=conta, forma_pagamento='crédito', parcelas_total=1))

    def perguntar(self, frase):
        self.dizer(frase)
        self.assertIsNotNone(self.tela, frase)
        return self.tela.text

    def test_moradia_soma_as_contas_e_a_luz_estimada(self):
        texto = self.perguntar('quanto vou pagar de moradia')
        for nome in ('Condominio', 'IPTU', 'IPTV', 'Internet', 'Conta de luz'):
            self.assertIn(nome, texto)
        self.assertIn('≈ R$ 81,76', texto)  # média ago/set/out
        self.assertIn('💰 Falta pagar: <b>R$ 1.001,76</b>', texto)  # 600+150+50+120+81,76

    def test_depois_de_pagar_o_iptu_conta_como_pago(self):
        self.agir(('settle', self.ids['IPTU'], '2026-11'))
        self.clicar('answer', 'Itaú')
        self.clicar('commit')
        texto = self.perguntar('quanto vou pagar de moradia')
        self.assertIn('✅ IPTU · pago R$ 150,00', texto)
        self.assertIn('💰 Falta pagar: <b>R$ 851,76</b>', texto)
        self.assertIn('Total: R$ 1.001,76 · já pago: R$ 150,00', texto)

    def test_cartao_soma_as_faturas_e_bate_com_o_a_pagar(self):
        abertos = self.engine._pay_month_open_items('2026-11')
        faturas = {i['nome']: float(i['valor']) for i in abertos if i.get('grupo') == 'bancos'}
        self.assertTrue({'Itaú', 'Mercado Pago', 'Infinitepay', 'Nubank'} <= set(faturas), faturas)
        total = sum(faturas.values())
        for frase in ('quanto vou pagar de cartão', 'quanto vou pagar de cartão de crédito', 'quanto vou pagar de faturas'):
            with self.subTest(frase=frase):
                texto = self.perguntar(frase)
                self.assertIn('💳 Faturas dos cartões', texto)
                for nome in ('Itaú', 'Mercado Pago', 'Infinitepay', 'Nubank'):
                    self.assertIn(nome, texto)
                self.assertIn(f'💰 Falta pagar: <b>{self.engine_money(total)}</b>', texto)

    def engine_money(self, valor):
        import telegram_experiencia as ux
        return ux.money(valor)

    def test_assinaturas_mostra_o_que_esta_no_cartao_sem_somar(self):
        texto = self.perguntar('quanto vou pagar de assinaturas')
        self.assertIn('No cartão (já dentro das faturas, não somado aqui): YouTube Premium', texto)

    def test_conta_citada_continua_na_tela_da_conta(self):
        texto = self.perguntar('quanto vou pagar no itaú')
        self.assertNotIn('Faturas dos cartões', texto)
        self.assertIn('Itaú', texto)

    def test_categoria_inexistente_sugere_as_que_existem(self):
        texto = self.perguntar('quanto vou pagar de xpto')
        self.assertIn('Não encontrei contas previstas', texto)
        self.assertIn('Moradia', texto)

    def test_fixos_por_categoria_e_filtro(self):
        tela = self.agir(('fixed_list', 0))
        self.assertIn('🏷 Moradia · <b>R$ 1.001,76</b> (5)', tela.text)
        self.assertIn('🏷 Assinaturas · <b>R$ 24,90</b> (1) · 💳 1 no cartão', tela.text)
        self.assertIn(('fixed_list', 0, 'Moradia'), self.acoes())
        tela = self.agir(('fixed_list', 0, 'Moradia'))
        self.assertIn('Fixos · Moradia', tela.text)
        self.assertNotIn('YouTube', tela.text)
        self.assertIn(('pagar_cat', 'Moradia', '2026-11', '2026-11'), self.acoes())
        tela = self.agir(('pagar_cat', 'Moradia', '2026-11', '2026-11'))
        self.assertIn('💰 Falta pagar: <b>R$ 1.001,76</b>', tela.text)

    def test_proximos_meses(self):
        texto = self.perguntar('quanto vou pagar de moradia nos próximos 2 meses')
        self.assertIn('Novembro 2026 a Dezembro 2026', texto)
        self.assertIn('Dezembro 2026 ·', texto)
