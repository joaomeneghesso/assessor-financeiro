"""Percursos até confirmação com banco descartável, incluindo clique repetido."""
import tempfile,unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
import database as db,services as svc,telegram_experiencia as ux

class BotoesFinais(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for mod in (db,svc):
            p=patch.object(mod,'DB_PATH',Path(self.tmp.name)/'fixture.db');p.start();self.addCleanup(p.stop)
        db.init_db();self.engine=ux.Experience(date_provider=lambda:date(2026,9,30));self.key='teste-final'
    def action(self,screen,kind):
        actions=[a for row in screen.rows for _,a in row if a[0]==kind]
        self.assertTrue(actions,f'Botão {kind} ausente: {screen.text}')
        return tuple(actions[0])
    def counts(self):
        with db.get_connection() as c:
            return tuple(c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('transacoes','compromissos','fatura_movimentos'))
    def test_limite_confirmacao_cancelamento_e_repeticao(self):
        before=self.counts();self.engine.act(self.key,('budget_start',))
        self.engine.handle_text(self.key,'Mercado');screen=self.engine.handle_text(self.key,'500')
        action=self.action(screen,'save_budget');self.engine.act(self.key,action)
        with self.assertRaises(ValueError):self.engine.act(self.key,action)
        self.assertEqual(before,self.counts())
        self.engine.act(self.key,('budget_start',));self.engine.handle_text(self.key,'Casa')
        self.engine.handle_text(self.key,'100');self.engine.act(self.key,('cancel',))
        with self.assertRaises(ValueError):self.engine.act(self.key,('save_budget',))
        self.assertEqual(before,self.counts())
    def test_horarios_invalidos_e_confirmacao_sem_movimento(self):
        before=self.counts();self.engine.act(self.key,('alert_hours',))
        self.engine.handle_text(self.key,'99:99 20:00 23:00 08:00')
        self.assertEqual(before,self.counts())
        screen=self.engine.handle_text(self.key,'09:00 20:00 23:00 08:00')
        action=self.action(screen,'save_hours');self.engine.act(self.key,action)
        with self.assertRaises(ValueError):self.engine.act(self.key,action)
        self.assertEqual(before,self.counts())
    def test_saldo_inicial_so_altera_base_sem_receita(self):
        before=self.counts();self.engine.act(self.key,('balance_initial',))
        screen=self.engine.handle_text(self.key,'1000')
        action=self.action(screen,'save_balance');self.engine.act(self.key,action)
        with self.assertRaises(ValueError):self.engine.act(self.key,action)
        self.assertEqual(before,self.counts())
        self.assertIsNotNone(db.buscar_saldo_mensal('2026-09'))
    def test_vincular_e_desvincular_preserva_lancamento_real(self):
        fixed=db.inserir_compromisso(dict(tipo='fixo',nome='Internet',categoria='Casa',valor=80,data_inicio='2026-09-01',dia_vencimento=25,conta_pagamento='Itaú',forma_pagamento='pix',ativo=1))
        tx=db.inserir_transacao(dict(data='2026-09-25',tipo='despesa',valor=80,categoria='Casa',descricao='Internet',conta='Itaú',forma_pagamento='pix',parcelas_total=1))
        before=self.counts();screen=self.engine.act(self.key,('link_existing',tx))
        if not any(a[0]=='choose_target' for row in screen.rows for _,a in row):
            screen=self.engine.act(self.key,self.action(screen,'pick_target'))
        screen=self.engine.act(self.key,self.action(screen,'choose_target'))
        action=self.action(screen,'commit_link');self.engine.act(self.key,action)
        with self.assertRaises(ValueError):self.engine.act(self.key,action)
        self.assertEqual(before,self.counts())
        screen=self.engine.act(self.key,('view','reconciliations'))
        screen=self.engine.act(self.key,self.action(screen,'unlink_preview'))
        self.engine.act(self.key,self.action(screen,'unlink'))
        self.assertEqual(before,self.counts())
