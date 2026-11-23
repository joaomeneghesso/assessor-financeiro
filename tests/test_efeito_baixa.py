"""Efeito no dinheiro na prévia e na confirmação (pedido do titular em 19/11/2026).

Caso de exemplo: saldo do Mercado Pago ajustado para 10.000,00; baixa do iCloud (fixo Pix,
33,45) paga pelo Mercado Pago. O saldo caiu para 9.966,55, mas a sobra prevista não
mudou (o valor já estava reservado em A pagar) e o titular achou que não tinha
descontado. Agora as telas mostram o saldo da conta antes → depois e explicam a sobra.
Caminho real (``dispatch_text`` + ações), banco temporário com migrations.
"""
from unittest.mock import patch

import database as db
import efeito_baixa
from tests.test_jornadas_ponta_a_ponta import JornadaBase, setUpModule, tearDownModule  # noqa: F401


class EfeitoNoDinheiroTests(JornadaBase):
    def setUp(self):
        super().setUp()
        self.ajustar_saldo('Mercado Pago', '10000,00')
        self.ajustar_saldo('Itaú', '1000')
        self.icloud = db.inserir_compromisso(dict(tipo='fixo', nome='iCloud', categoria='Assinaturas', valor=33.45,
                                                  data_inicio='2026-06-10', dia_vencimento=30, conta_pagamento='Itaú',
                                                  forma_pagamento='pix', ativo=True))

    def test_baixa_do_icloud_mostra_saldo_antes_depois_e_sobra_sem_mudanca(self):
        self.agir(('settle', self.icloud, '2026-11'))
        self.assertEqual('account', self.estagio())
        previa = self.clicar('answer', 'Mercado Pago')
        self.assertIn('🏦 Ao salvar: Mercado Pago R$ 10.000,00 → R$ 9.966,55', previa.text)
        salvo = self.clicar('commit')
        self.assertIn('✅ Registro salvo', salvo.text)
        self.assertIn('🏦 Mercado Pago: R$ 10.000,00 → <b>R$ 9.966,55</b>', salvo.text)
        self.assertIn('📊 Sobra prevista: sem mudança — este valor já estava reservado em A pagar.', salvo.text)

    def test_gasto_comum_mostra_a_sobra_caindo(self):
        tela = self.registrar('gastei 50 no mercado', ['pix', 'Itaú'])
        self.assertIn('🏦 Itaú: R$ 1.000,00 → <b>R$ 950,00</b>', tela.text)
        self.assertRegex(tela.text, r'📊 Sobra prevista: R\$ [\d.]+,\d\d → R\$ [\d.]+,\d\d')

    def test_entrada_aumenta_o_saldo(self):
        tela = self.registrar('recebi 200 de reembolso no itaú', ['pix'])
        self.assertIn('🏦 Itaú: R$ 1.000,00 → <b>R$ 1.200,00</b>', tela.text)

    def test_credito_avisa_que_vai_para_a_fatura(self):
        tela = self.registrar('gastei 80 no crédito nubank em farmácia', ['não'])
        self.assertIn('💳 No crédito: não saiu do saldo agora; entra na fatura do cartão.', tela.text)
        self.assertNotIn('🏦 Nubank:', tela.text)

    def test_falha_no_calculo_nunca_impede_o_registro(self):
        with patch.object(efeito_baixa.svc, 'calcular_caixa_por_conta_mes', side_effect=RuntimeError('falha simulada')):
            tela = self.registrar('gastei 10 no mercado', ['pix', 'Itaú'])
        self.assertIn('✅ Registro salvo', tela.text)
        self.assertNotIn('Efeito no seu dinheiro', tela.text)

    def test_privacidade_esconde_os_valores(self):
        self.engine.session(self.KEY).privacy = True
        tela = self.registrar('gastei 50 no mercado', ['pix', 'Itaú'])
        self.assertNotIn('R$ 950,00', tela.text)
