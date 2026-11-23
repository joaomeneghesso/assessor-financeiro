import tempfile,unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
import database as db,services as svc,compromissos as comp
import telegram_experiencia as ux
import saldos_edicao
import fatura_conferencia as fc

class ConferenciaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',Path(self.temp.name)/'db.sqlite');p.start();self.addCleanup(p.stop)
        db.init_db()
        self.exp=ux.Experience(date_provider=lambda:date(2026,9,30))
        for name,value in [('Celular',49.99),('YouTube',12.95)]:
            db.inserir_compromisso(dict(tipo='fixo',nome=name,categoria='Assinaturas',conta_pagamento='Itaú',forma_pagamento='crédito',valor=value,data_inicio='2026-09-01',dia_vencimento=16,ativo=1))
        db.inserir_transacao(dict(data='2026-09-01',tipo='despesa',valor=1181.2,categoria='Outros',descricao='Composição restante',conta='Itaú',forma_pagamento='crédito',parcelas_total=1))
        self.mov=db.inserir_fatura_movimento(dict(ano_mes='2026-09',conta_cartao='Itaú',tipo_movimento='pagamento_total',valor=1181.2,data_movimento='2026-09-27',conta_origem='Mercado Pago'))
        saldos_edicao.confirmar('2026-09','Mercado Pago',5000,saldos_edicao.capturar('2026-09'),'fixture')
        self.before_mov=dict(db.buscar_fatura_movimento_por_id(self.mov))
        self.before_fatura=comp.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
    def confirm(self):
        return fc.confirmar('2026-09','Itaú',self.mov,'1231,23',self.before_mov,self.before_fatura,'fixture','Total quitado confirmado; diferença de composição não identificada.')
    def test_quitacao_preserva_saldo_atual_e_outubro_sem_nova_transacao(self):
        before=svc.obter_metricas_resultado_mes('2026-09')
        tx=[dict(x) for x in db.buscar_transacoes_por_mes('2026-09')]
        rows=[dict(x) for x in db.listar_compromissos()]
        self.confirm()
        after=svc.obter_metricas_resultado_mes('2026-09')
        self.assertAlmostEqual(before['saldo_disponivel'],after['saldo_disponivel'])
        self.assertAlmostEqual(62.94,after['saldo_projetado']-before['saldo_projetado'])
        f=comp.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
        self.assertAlmostEqual(0,f['saldo_restante'])
        self.assertEqual('paga',f['status'])
        self.assertAlmostEqual(-12.91,f['ajuste_conferencia'])
        self.assertEqual(tx,[dict(x) for x in db.buscar_transacoes_por_mes('2026-09')])
        self.assertEqual(rows,[dict(x) for x in db.listar_compromissos()])
        self.assertAlmostEqual(62.94,comp.calcular_fatura_unificada('2026-10','Itaú',somente_cartao=True)['saldo_restante'])
        self.assertFalse(any(x.get('origem')=='banco_agregado' for x in self.exp.obligations('2026-09')))
        self.assertEqual(1,len(db.listar_fatura_movimentos('2026-09')))
    def test_repeticao_nao_corrige_base_ou_pagamento_duas_vezes(self):
        self.confirm();snapshot=saldos_edicao.capturar('2026-09')
        result=self.confirm()
        self.assertTrue(result['repetido'])
        self.assertEqual(snapshot,saldos_edicao.capturar('2026-09'))
    def test_falha_auditoria_reverte_pagamento_e_base(self):
        snapshot=saldos_edicao.capturar('2026-09')
        with patch.object(db,'registrar_auditoria',side_effect=RuntimeError('sintético')):
            with self.assertRaises(RuntimeError):self.confirm()
        self.assertEqual(self.before_mov,dict(db.buscar_fatura_movimento_por_id(self.mov)))
        self.assertEqual(snapshot,saldos_edicao.capturar('2026-09'))
        self.assertIsNone(fc.obter('2026-09','Itaú'))
    def test_previa_pagamento_obsoleta_nao_altera(self):
        with db.get_connection() as c:c.execute('UPDATE fatura_movimentos SET valor=1100 WHERE id=?',(self.mov,))
        with self.assertRaisesRegex(ValueError,'pagamento mudou'):self.confirm()
        self.assertIsNone(fc.obter('2026-09','Itaú'))
    def test_previa_composicao_obsoleta_nao_altera(self):
        db.inserir_transacao(dict(data='2026-09-20',tipo='despesa',valor=10,categoria='Outros',descricao='Outra compra',conta='Itaú',forma_pagamento='crédito',parcelas_total=1))
        with self.assertRaisesRegex(ValueError,'composição mudou'):self.confirm()
    def test_compra_real_posterior_nao_e_escondida_pela_conferencia(self):
        self.confirm()
        db.inserir_transacao(dict(data='2026-09-20',tipo='despesa',valor=10,categoria='Outros',descricao='Outra compra',conta='Itaú',forma_pagamento='crédito',parcelas_total=1))
        self.assertAlmostEqual(10,comp.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)['saldo_restante'])
    def test_pix_debito_transferencia_continuam_individuais(self):
        ids=[]
        for method in ['pix','débito','transferência']:
            ids.append(db.inserir_compromisso(dict(tipo='fixo',nome=method,categoria='Outros',conta_pagamento='Itaú',forma_pagamento=method,valor=10,data_inicio='2026-09-01',dia_vencimento=16,ativo=1)))
        self.before_fatura=comp.calcular_fatura_unificada('2026-09','Itaú',somente_cartao=True)
        self.confirm()
        items=self.exp.obligations('2026-09')
        self.assertEqual(set(ids),{x['id'] for x in items if x.get('origem')=='compromisso'})
