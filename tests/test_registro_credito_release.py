"""Percurso real de cadastro no crédito, com o esquema de competência instalado."""
import importlib.util,tempfile,unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import database as db,services as svc,telegram_experiencia as ux

class RegistroCreditoFinal(unittest.TestCase):
 def test_credito_confirmado_tem_competencia_sem_baixa_de_caixa_duplicidade_ou_pagamento(self):
  with tempfile.TemporaryDirectory() as temp:
   target=Path(temp)/'fixture.db'
   with patch.object(db,'DB_PATH',target),patch.object(svc,'DB_PATH',target):
    db.init_db()
    spec=importlib.util.spec_from_file_location('fixture_competencia',Path(__file__).resolve().parents[1]/'migrations/0004_competencia_faturas.py')
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with db.get_connection() as conn:migration.upgrade(conn)
    db.definir_saldo_inicial_conta_mes('2026-09','Nubank',1000)
    with db.get_connection() as conn:cash_before=[tuple(r) for r in conn.execute('SELECT * FROM saldos_mensais_contas')]
    engine=ux.Experience(date_provider=lambda:date(2026,9,30));key='credito_final';engine.session(key).month='2026-09'
    def preview():
     engine.begin(key,'despesa')
     for answer in ['35,90','Café fictício','crédito','não','Nubank','2026-10']:  # P7: parcelas só após crédito; data padrão hoje
      screen=engine.handle_text(key,answer)
     self.assertEqual('confirm',engine.session(key).stage)
     return screen
    screen=preview()
    with db.get_connection() as conn:self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM transacoes').fetchone()[0])
    tokens=engine.tokens_for(key,screen)
    action=next(engine.resolve(key,token) for row,buttons in zip(screen.rows,tokens) for (_,candidate),(_,token) in zip(row,buttons) if candidate[0]=='commit')
    engine.act(key,action);engine.act(key,action)
    preview();engine.act(key,('cancel',))
    with db.get_connection() as conn:
     rows=conn.execute('SELECT valor,forma_pagamento,data_compra,competencia_fatura FROM transacoes').fetchall()
     self.assertEqual(1,len(rows));self.assertAlmostEqual(35.90,rows[0][0])
     self.assertEqual('crédito',rows[0][1]);self.assertEqual('2026-09-30',rows[0][2]);self.assertEqual('2026-10',rows[0][3])
     self.assertEqual(cash_before,[tuple(r) for r in conn.execute('SELECT * FROM saldos_mensais_contas')])
     self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM fatura_movimentos').fetchone()[0])
     self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM compromissos').fetchone()[0])
