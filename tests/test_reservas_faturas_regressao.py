"""Contratos de caixa independentes da composição contábil dos cartões."""
import tempfile,unittest,random
from pathlib import Path
from unittest.mock import patch
import database as db,services as svc,compromissos as comp
from saldo_resumo import resumir_saldo

class ReservasRegressao(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for mod in (db,svc):
            p=patch.object(mod,'DB_PATH',Path(self.tmp.name)/'db.sqlite');p.start();self.addCleanup(p.stop)
        db.init_db();db.definir_saldo_inicial_conta_mes('2026-09','Mercado Pago',10000)
    def compra(self,bank,value,name='Compra',month='2026-09'):
        return db.inserir_transacao(dict(data=month+'-01',tipo='despesa',valor=value,categoria='Outros',descricao=name,conta=bank,forma_pagamento='crédito',parcelas_total=1))
    def fixo(self,bank,value,name='Mensalidade',method='crédito'):
        return db.inserir_compromisso(dict(tipo='fixo',nome=name,categoria='Outros',conta_pagamento=bank,forma_pagamento=method,valor=value,data_inicio='2026-09-01',dia_vencimento=10,ativo=1))
    def pago(self,bank,value,month='2026-09'):
        db.inserir_fatura_movimento(dict(ano_mes=month,conta_cartao=bank,tipo_movimento='pagamento_total',valor=value,data_movimento=month+'-20',conta_origem='Mercado Pago'))
    def reserva(self,month='2026-09'):
        m=svc.obter_metricas_resultado_mes(month);s=resumir_saldo(m)
        self.assertAlmostEqual(s['saldo_atual']+s['a_receber']-s['reservas_liquidas'],s['saldo_final'],places=2)
        return s['reservas_liquidas']
    def test_credito_em_outro_cartao_nao_abate_nubank(self):
        self.compra('Infinitepay',299.35);self.pago('Infinitepay',362.29);self.fixo('Nubank',1240.8)
        m=svc.obter_metricas_resultado_mes('2026-09')
        self.assertAlmostEqual(1240.8,self.reserva())
        self.assertAlmostEqual(10000-362.29,m['saldo_disponivel'])
        self.assertAlmostEqual(10000-362.29-1240.8,m['saldo_projetado'])
        self.assertAlmostEqual(-62.94,comp.calcular_fatura_unificada('2026-09','Infinitepay',somente_cartao=True)['saldo_restante'])
    def test_credito_herdado_so_abate_o_mes_seguinte_do_mesmo_cartao(self):
        self.compra('Itaú',100,month='2026-08');self.pago('Itaú',150,month='2026-08')
        self.fixo('Itaú',80);self.fixo('Nubank',120)
        self.assertAlmostEqual(150,self.reserva())
        self.assertAlmostEqual(30,comp.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)['saldo_restante'])
    def test_mesmo_item_real_nao_e_reservado_duas_vezes(self):
        self.fixo('Nubank',50,'Plano');self.compra('Nubank',50,'Plano')
        self.assertAlmostEqual(50,self.reserva())
    def test_itens_independentes_do_mesmo_cartao_continuam_somados(self):
        self.fixo('Nubank',50,'Plano');self.compra('Nubank',50,'Mercado')
        self.assertAlmostEqual(100,self.reserva())
    def test_estorno_nao_vira_dinheiro_nem_abate_outro_cartao(self):
        self.compra('Infinitepay',20);self.fixo('Nubank',90)
        db.inserir_fatura_movimento(dict(ano_mes='2026-09',conta_cartao='Infinitepay',tipo_movimento='estorno',valor=50,data_movimento='2026-09-20'))
        self.assertAlmostEqual(90,self.reserva())
        self.assertAlmostEqual(10000,svc.obter_metricas_resultado_mes('2026-09')['saldo_disponivel'])
    def test_pix_debito_boleto_transferencia_nao_sao_credito_de_cartao(self):
        for method in ['pix','débito','boleto','transferência']:self.fixo('Mercado Pago',10,method,method)
        self.assertAlmostEqual(40,self.reserva())
    def test_pagamento_parcial_reserva_so_o_restante(self):
        self.fixo('Nubank',120);self.pago('Nubank',35)
        self.assertAlmostEqual(85,self.reserva())
    def test_matriz_de_centavos_por_tres_cartoes(self):
        rng=random.Random(404)
        for bank in ['Nubank','Infinitepay','Mercado Pago']:
            charge=round(rng.randint(1,99999)/100,2);payment=round(rng.randint(1,99999)/100,2)
            self.compra(bank,charge);self.pago(bank,payment)
        expected=sum(max(0,comp.calcular_fatura_unificada('2026-09',b,somente_cartao=True)['saldo_restante']) for b in ['Nubank','Infinitepay','Mercado Pago'])
        self.assertAlmostEqual(expected,self.reserva(),places=2)
