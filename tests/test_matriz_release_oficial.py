"""Matriz de vigência/caixa e leitura sem efeitos, em banco descartável."""
import tempfile,unittest,calendar
from pathlib import Path
from datetime import date,timedelta
from unittest.mock import patch
import database as db,services as svc,compromissos as comp,fixos_edicao as fx,saldos_edicao as cash
from saldo_resumo import resumir_saldo

class MatrizRelease(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',Path(self.tmp.name)/'test.db');p.start();self.addCleanup(p.stop)
        db.init_db()
    def movements(self):
        with db.get_connection() as c:
            return {table:[tuple(r) for r in c.execute('SELECT * FROM '+table)] for table in ('transacoes','fatura_movimentos','transferencias_caixa')}
    def test_versionamento_em_cinco_formas_e_tres_viradas(self):
        for month in ['2026-10','2027-01','2028-02']:
            for method in ['pix','crédito','débito','transferência','boleto']:
                with self.subTest(month=month,method=method):
                    name='Plano '+month+' '+method
                    ident=db.inserir_compromisso(dict(tipo='fixo',nome=name,categoria='Casa',valor=49.99,data_inicio='2026-01-01',dia_vencimento=31,conta_pagamento='Itaú',forma_pagamento=method,ativo=1))
                    before=self.movements();fx.salvar(fx.preparar(ident,'valor','62,94',month),'fixture')
                    self.assertEqual(before,self.movements())
                    previous=date.fromisoformat(month+'-01')-timedelta(days=1)
                    old=db.buscar_compromisso_por_id(ident)
                    self.assertEqual(previous.isoformat(),old['data_fim'])
                    for period,expected in [(previous.strftime('%Y-%m'),49.99),(month,62.94)]:
                        rows=[r for r in comp.projetar_compromissos_mes(period) if r['nome']==name]
                        self.assertEqual([expected],[r['valor'] for r in rows])
    def test_edicao_de_saldo_preserva_movimentos_em_matriz_de_centavos(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        db.definir_saldo_inicial_conta_mes('2026-09','Nubank',123.45)
        db.inserir_transacao(dict(data='2026-09-20',tipo='despesa',valor=10.01,categoria='Casa',descricao='Teste',conta='Itaú',forma_pagamento='pix',parcelas_total=1))
        before=self.movements()
        for value in ['0','-0,01','0,01','62,94','1231,23','1240,80','99999,99']:
            with self.subTest(value=value):
                cash.confirmar('2026-09','Itaú',value,cash.capturar('2026-09'),'fixture')
                expected=float(value.replace(',','.'))
                positions=svc.calcular_caixa_por_conta_mes('2026-09')
                self.assertAlmostEqual(expected,positions['contas']['Itaú']['disponivel'],places=2)
                self.assertAlmostEqual(expected+123.45,positions['total_disponivel'],places=2)
                self.assertEqual(before,self.movements())
                s=resumir_saldo(svc.obter_metricas_resultado_mes('2026-09'))
                self.assertAlmostEqual(s['saldo_atual']+s['a_receber']-s['reservas_liquidas'],s['saldo_final'],places=2)
    def test_dashboard_backend_eh_leitura_e_proibe_escrita_acidental(self):
        before=self.movements()
        self.assertEqual(before,self.movements())
        with db.read_only_mode():
            with self.assertRaises(Exception):
                with db.get_connection() as c:c.execute('DELETE FROM compromissos')
        self.assertEqual(before,self.movements())
