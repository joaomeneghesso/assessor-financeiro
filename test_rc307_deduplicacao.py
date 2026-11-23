import unittest
from unittest.mock import patch
import compromissos

class TestRC307Dedupe(unittest.TestCase):
    def base(self,name,value,orig='compromisso',tipo='fixo',date='2026-09-10'):
        return {'origem':orig,'tipo':tipo,'id':1,'nome':name,'categoria':'Assinaturas','conta_pagamento':'Itaú','forma_pagamento':'crédito','valor':value,'data':date}
    def ctx(self,itens):
        return patch.object(compromissos,'obter_itens_base_pagamentos_mes',return_value=itens), patch.object(compromissos,'listar_fatura_movimentos',return_value=[]), patch.object(compromissos,'obter_primeira_competencia_financeira',return_value='2026-09')
    def test_real_diferente_nao_remove_previsoes(self):
        prev=[self.base('Wellhub',91.70),self.base('YouTube premium',13.13)]
        real=self.base('Almoço',45.0,'transacao','transacao')
        p1,p2,p3=self.ctx([*prev,real])
        with p1,p2,p3:
            r=compromissos.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
        self.assertAlmostEqual(149.83,r['valor_bruto'],2)
        self.assertEqual(0,len(r['itens_previstos_ignorados']))
    def test_mesmo_item_real_remove_so_duplicata(self):
        prev=[self.base('Wellhub',91.70),self.base('YouTube premium',13.13)]
        real=self.base('Wellhub',91.70,'transacao','transacao')
        p1,p2,p3=self.ctx([*prev,real])
        with p1,p2,p3:
            r=compromissos.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
        self.assertAlmostEqual(104.83,r['valor_bruto'],2)
        self.assertEqual(['Wellhub'],[x['nome'] for x in r['itens_previstos_ignorados']])
    def test_parcela_nome_normalizado_deduplica(self):
        prev=self.base('Notebook',100.0,'compromisso','parcelamento')
        prev['parcela_atual']=3; prev['parcelas_total']=10
        real=self.base('Notebook (3/10)',100.0,'transacao','transacao')
        real['parcela_atual']=3; real['parcelas_total']=10
        p1,p2,p3=self.ctx([prev,real])
        with p1,p2,p3:
            r=compromissos.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
        self.assertAlmostEqual(100.0,r['valor_bruto'],2)
        self.assertEqual(1,len(r['itens_previstos_ignorados']))
    def test_mesmo_nome_valor_diferente_nao_remove(self):
        prev=self.base('Wellhub',91.70)
        real=self.base('Wellhub',99.90,'transacao','transacao')
        p1,p2,p3=self.ctx([prev,real])
        with p1,p2,p3:
            r=compromissos.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
        self.assertAlmostEqual(191.60,r['valor_bruto'],2)
        self.assertEqual(0,len(r['itens_previstos_ignorados']))

if __name__=='__main__': unittest.main()
