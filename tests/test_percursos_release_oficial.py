"""Término dos caminhos pouco usados e compatibilidade de botões antigos."""
import tempfile,unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
import database as db,services as svc,telegram_experiencia as ux

class PercursosRelease(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',Path(self.tmp.name)/'fixture.db');p.start();self.addCleanup(p.stop)
        db.init_db();self.e=ux.Experience(date_provider=lambda:date(2026,9,30));self.key='release'
        for n in range(14):db.definir_saldo_inicial_conta_mes('2026-09','Conta '+str(n),100)
        db.definir_saldo_inicial_conta_mes('2026-09','Nubank',1000)
    def click(self,screen,kind):
        tokens=self.e.tokens_for(self.key,screen)
        for row,buttons in zip(screen.rows,tokens):
            for (_,action),(_,token) in zip(row,buttons):
                if action[0]==kind:
                    resolved=self.e.resolve(self.key,token);self.assertEqual(tuple(action),tuple(resolved))
                    return self.e.act(self.key,resolved)
        self.fail(f'Botão {kind} não encontrado: {screen.text}')
    def financial(self):
        with db.get_connection() as c:
            return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('transacoes','compromissos','fatura_movimentos','transferencias_caixa')}
    def pause(self):
        self.e.begin(self.key,'receita');self.e.handle_text(self.key,'20')
        return self.e.act(self.key,('view','home'))
    def test_pausar_descartar_e_recomecar_nao_grava(self):
        before=self.financial();screen=self.pause();self.click(screen,'discard_suspended')
        self.pause();screen=self.e.act(self.key,('start','despesa'));self.click(screen,'discard_and_start')
        self.e.act(self.key,('cancel',));self.pause()
        screen=self.e.act(self.key,('view','register'));self.click(screen,'discard_and_register')
        self.assertEqual(before,self.financial())
    def test_contas_paginas_limpar_busca_e_botoes_legados_de_saldo(self):
        before=self.financial();self.e.begin(self.key,'receita');self.e.handle_text(self.key,'20')
        self.e.handle_text(self.key,'Salário');screen=self.e.handle_text(self.key,'pix');self.click(screen,'account_choice_page')
        self.e.act(self.key,('cancel',));self.e.act(self.key,('search',));self.e.handle_text(self.key,'nada')
        self.e.act(self.key,('clear_search',));self.assertEqual('',self.e.session(self.key).search)
        self.e.act(self.key,('balance_start',));self.e.act(self.key,('balance_account','Nubank','2026-09'))
        self.assertEqual(before,self.financial())
    def test_fatura_paginas_previa_reinicio_e_cancelamento(self):
        db.inserir_transacao(dict(data='2026-09-20',tipo='despesa',valor=120,categoria='Casa',descricao='Compra',conta='Nubank',forma_pagamento='crédito',parcelas_total=1))
        before=self.financial();screen=self.e.act(self.key,('invoice_begin','B_nubank','2026-09'))
        screen=self.click(screen,'invoice_pay_total');screen=self.click(screen,'invoice_account_page')
        screen=self.click(screen,'invoice_account_select')
        screen=self.e.answer(self.key,'20');self.click(screen,'invoice_preview')
        self.e.act(self.key,('invoice_restart','B_nubank','2026-09'));self.e.act(self.key,('cancel',))
        self.assertEqual(before,self.financial())
    def test_simular_variantes_e_cronograma_ate_ultima_pagina(self):
        before=self.financial();self.e.begin(self.key,'simulate')
        self.e.session(self.key).draft.update(valor=120,descricao='Computador',categoria='Eletrônicos',conta='Nubank',forma_pagamento='crédito',data='2026-09-30',parcelas_total=12)
        self.e.session(self.key).stage='confirm'
        for count in [1,3,6]:self.e.act(self.key,('simulate_variant',count))
        self.e.session(self.key).draft['parcelas_total']=12
        screen=self.e.act(self.key,('installment_schedule',0));screen=self.click(screen,'installment_schedule')
        self.assertIn('12',screen.text);self.e.act(self.key,('cancel',));self.assertEqual(before,self.financial())
    def test_ajuda_longa_e_paginacao_de_contas_a_pagar(self):
        before=self.financial();screen=self.e.advanced_help(self.key,'ajuda','Texto de orientação. '*600)
        screen=self.click(screen,'help_page');self.assertGreater(self.e.session(self.key).help_page,0)
        for n in range(9):
            db.inserir_compromisso(dict(tipo='fixo',nome='Conta mensal '+str(n),categoria='Casa',valor=10,data_inicio='2026-09-01',dia_vencimento=10,conta_pagamento='Conta '+str(n),forma_pagamento='pix',ativo=1))
        before=self.financial();screen=self.e.act(self.key,('pay_month','2026-09'));self.click(screen,'pay_month_page')
        self.assertEqual(before,self.financial())
    def test_conciliacao_legada_preserva_caixa_e_nao_recria_pagamentos(self):
        # Saldo geral antigo e marcação legada sem transação vinculada.
        with db.get_connection() as c:c.execute('DELETE FROM saldos_mensais_contas');c.execute('DELETE FROM saldos_mensais')
        db.definir_saldo_inicial_mes('2026-08',1000)
        ident=db.inserir_compromisso(dict(tipo='fixo',nome='Legado',categoria='Casa',valor=50,data_inicio='2026-08-01',data_fim='2026-08-31',dia_vencimento=10,conta_pagamento='Itaú',forma_pagamento='pix',ativo=1))
        db.marcar_checklist_pagamento('2026-08',f'C{ident}','pago')
        before=self.financial();old=svc.obter_metricas_resultado_mes('2026-09')['saldo_disponivel']
        screen=self.e.act(self.key,('reconcile_baseline_preview',));self.click(screen,'reconcile_baseline_commit')
        self.assertAlmostEqual(old,svc.obter_metricas_resultado_mes('2026-09')['saldo_disponivel'],places=2)
        self.assertEqual(before,self.financial())
        with self.assertRaises(ValueError):self.e.act(self.key,('reconcile_baseline_commit',))
