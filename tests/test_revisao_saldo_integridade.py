"""Contratos financeiros e falhas de gravação, sempre em banco temporário."""
import sqlite3
import threading
from contextlib import closing
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from unittest.mock import patch

import assessor_orientacao as orient
import compromissos as comp
import database as db
import fixos_edicao as fx
import services as svc
import saldos_edicao as saldo
import telegram_experiencia as ux
from saldo_resumo import resumir_saldo
from sqlite_backup import backup_sqlite_consistente


class RevisaoIntegridade(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'financeiro.db'
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',self.path);p.start();self.addCleanup(p.stop)
        db.init_db()
        self.exp=ux.Experience(date_provider=lambda:date(2026,9,30))

    def tx(self,kind,value,account='Itaú',method='pix'):
        return db.inserir_transacao(dict(data='2026-09-20',tipo='receita' if kind=='entrada' else kind,valor=value,
            categoria='Outros',descricao='Movimento sintético',conta=account,
            forma_pagamento=method,mensagem_original='fixture',parcelas_total=1))

    def financial(self):
        with db.get_connection() as c:
            return {name:c.execute('SELECT * FROM '+name+' ORDER BY id').fetchall()
                    for name in ('transacoes','fatura_movimentos','transferencias_caixa')}

    def fixed(self,**changes):
        row=dict(tipo='fixo',nome='Plano teste',categoria='Outros',conta_pagamento='Itaú',
                 forma_pagamento='pix',valor=50,dia_vencimento=10,data_inicio='2026-06-01',ativo=True)
        row.update(changes);return db.inserir_compromisso(row)

    def guided(self,**changes):
        row=dict(nome='Conta nova',categoria='Outros',conta_pagamento='Itaú',
                 forma_pagamento='pix',valor=60,dia_vencimento=10,data_inicio='2026-09',_confirmacao_id='teste-confirmacao')
        row.update(changes);return row

    def test_saldo_informado_e_atual_nao_receita_e_atualiza_previsao(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        self.tx('entrada',200);self.tx('despesa',80)
        before=self.financial();old=svc.obter_metricas_resultado_mes('2026-09')
        base=saldo.confirmar('2026-09','Itaú','900',saldo.capturar('2026-09'),'teste')
        self.assertEqual(780,base)
        self.assertAlmostEqual(900,svc.calcular_caixa_por_conta_mes('2026-09')['total_disponivel'])
        new=svc.obter_metricas_resultado_mes('2026-09')
        self.assertAlmostEqual(-220,new['saldo_projetado']-old['saldo_projetado'])
        self.assertEqual(before,self.financial())
        self.assertAlmostEqual(780,db.buscar_saldo_mensal('2026-09')['saldo_inicial'])

    def test_saldo_zero_e_negativo_sao_preservados(self):
        for value in ('0','-50,25'):
            saldo.confirmar('2026-09','Nubank',value,saldo.capturar('2026-09'),'teste')
            expected=0 if value=='0' else -50.25
            self.assertAlmostEqual(expected,svc.calcular_caixa_por_conta_mes('2026-09')['total_disponivel'])
            self.assertAlmostEqual(expected,svc.obter_metricas_resultado_mes('2026-09')['saldo_projetado'])

    def test_ajuste_preserva_outro_banco_e_normaliza_nome(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',100)
        db.definir_saldo_inicial_conta_mes('2026-09','Nubank',200)
        saldo.confirmar('2026-09','itau','150',saldo.capturar('2026-09'),'teste')
        caixa=svc.calcular_caixa_por_conta_mes('2026-09')
        self.assertEqual(350,caixa['total_disponivel'])
        self.assertEqual(200,caixa['contas']['Nubank']['disponivel'])
        self.assertEqual(2,len(db.buscar_saldos_contas_mes('2026-09')))

    def test_transferencia_conserva_total_e_tela_usa_caixa_real(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        db.definir_saldo_inicial_conta_mes('2026-09','Nubank',200)
        db.inserir_transferencia_caixa(dict(data='2026-09-20',valor=100,conta_origem='Itaú',conta_destino='Nubank'))
        caixa=svc.calcular_caixa_por_conta_mes('2026-09')
        self.assertEqual(1200,caixa['total_disponivel'])
        self.assertEqual(900,caixa['contas']['Itaú']['disponivel'])
        self.assertEqual(300,caixa['contas']['Nubank']['disponivel'])
        screen=self.exp._balance_account_screen('teste','Nubank','2026-09')
        self.assertIn('R$ 300,00',screen.text)

    def test_primeiro_ajuste_preserva_saldos_herdados_outros_bancos(self):
        db.definir_saldo_inicial_conta_mes('2026-08','Itaú',1000)
        db.definir_saldo_inicial_conta_mes('2026-08','Nubank',200)
        expected=saldo.capturar('2026-09')
        self.assertTrue(expected['caixa']['herdado_auto'])
        self.assertTrue(resumir_saldo(svc.obter_metricas_resultado_mes('2026-09'))['herdado_auto'])
        saldo.confirmar('2026-09','Itaú','950',expected,'teste')
        caixa=svc.calcular_caixa_por_conta_mes('2026-09')
        self.assertEqual(200,caixa['contas']['Nubank']['disponivel'])
        self.assertEqual(1150,caixa['total_disponivel'])

    def test_confirmacao_saldo_na_virada_mes_expira_sem_gravar(self):
        self.exp.act('teste',('cash_setup_start',))
        self.exp.handle_text('teste','Nubank');self.exp.handle_text('teste','123,45')
        self.exp.date_provider=lambda:date(2026,10,1)
        with self.assertRaisesRegex(ValueError,'mês mudou'):self.exp._cash_setup_commit('teste')
        self.assertEqual([],db.buscar_saldos_contas_mes('2026-09'))

    def test_ajuste_com_auditoria_falha_reverte_todas_bases(self):
        expected=saldo.capturar('2026-09')
        with patch.object(db,'registrar_auditoria',side_effect=RuntimeError('falha sintética')):
            with self.assertRaises(RuntimeError):saldo.confirmar('2026-09','Itaú','100',expected,'teste')
        self.assertEqual(expected,saldo.capturar('2026-09'))

    def test_previa_obsoleta_nao_grava(self):
        expected=saldo.capturar('2026-09');self.tx('entrada',5)
        with self.assertRaisesRegex(ValueError,'mudaram desde a prévia'):
            saldo.confirmar('2026-09','Itaú','100',expected,'teste')
        self.assertEqual([],db.buscar_saldos_contas_mes('2026-09'))

    def test_saldo_geral_que_seria_ignorado_e_bloqueado(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',100)
        with self.assertRaisesRegex(ValueError,'saldos por conta'):
            orient.configurar_saldo('teste','2026-09',900,None)
        self.assertIsNone(db.buscar_saldo_mensal('2026-09'))
        self.assertIn('saldo',svc.definir_saldo_inicial_formatado('2026-09',900).lower())
        self.assertIsNone(db.buscar_saldo_mensal('2026-09'))

    def test_primeira_conta_cadastra_saldo_sem_movimento(self):
        before=self.financial()
        self.exp.act('teste',('cash_setup_start',))
        self.assertEqual('cash_setup_account_name',self.exp.session('teste').stage)
        self.exp.handle_text('teste','Nubank');self.exp.handle_text('teste','123,45')
        self.exp._cash_setup_commit('teste')
        self.assertEqual(before,self.financial())
        self.assertEqual(123.45,svc.calcular_caixa_por_conta_mes('2026-09')['total_disponivel'])

    def test_nova_condicao_nao_pode_reabrir_versao_antiga(self):
        old=self.fixed();fx.salvar(fx.preparar(old,'valor','60','2026-09'),'teste')
        before=self.financial()
        with self.assertRaisesRegex(ValueError,'sobrepõe'):svc.remover_termino_fixo(old,'teste')
        with self.assertRaisesRegex(ValueError,'sobrepõe'):
            fx.salvar(fx.preparar(old,'termino','2026-12-31'),'teste')
        self.assertEqual('2026-08-31',db.buscar_compromisso_por_id(old)['data_fim'])
        self.assertEqual(before,self.financial())

    def test_duplicidades_nao_confundem_versoes_adjacentes(self):
        old=self.fixed();fx.salvar(fx.preparar(old,'vencimento','11','2026-09'),'teste')
        fx.salvar(fx.preparar(old,'vencimento','11'),'teste')
        self.assertEqual([],svc.revisar_fixos_duplicados())
        self.fixed(dia_vencimento=11,data_inicio='2026-09-01')
        self.assertTrue(svc.revisar_fixos_duplicados())

    def test_cadastro_falha_auditoria_reverte_registro(self):
        with patch.object(svc,'registrar_auditoria',side_effect=RuntimeError('auditoria sintética')):
            with self.assertRaises(RuntimeError):svc.cadastrar_fixo_guiado(self.guided(),'teste')
        self.assertEqual([],db.listar_compromissos())

    def test_falha_resumo_apos_commit_informa_sucesso_salvo(self):
        with patch.object(svc,'calcular_fatura_unificada',side_effect=[dict(saldo_restante=0),RuntimeError('consulta sintética')]):
            with self.assertLogs(level='ERROR') as logs:
                result=svc.cadastrar_fixo_guiado(self.guided(forma_pagamento='crédito'),'teste')
        self.assertTrue(any('resumo da fatura indisponível' in line for line in logs.output))
        self.assertTrue(result['resumo_indisponivel'])
        self.assertIsNotNone(db.buscar_compromisso_por_id(result['compromisso']['id']))
        self.assertEqual(1,len(db.listar_compromissos()))
        self.assertEqual([],db.buscar_transacoes_por_mes('2026-09'))

    def test_confirmacao_repetida_tem_mesmo_id_e_auditoria_unica(self):
        first=svc.cadastrar_fixo_guiado(self.guided(),'teste')
        second=svc.cadastrar_fixo_guiado(self.guided(),'teste')
        self.assertEqual(first['compromisso']['id'],second['compromisso']['id'])
        self.assertTrue(second['repetido'])
        self.assertEqual(1,len(db.listar_auditoria('compromissos',first['compromisso']['id'])))

    def test_confirmacao_nao_permite_payload_ou_usuario_diferente(self):
        svc.cadastrar_fixo_guiado(self.guided(),'teste')
        for row,user in [(self.guided(valor=61),'teste'),(self.guided(),'outro')]:
            with self.assertRaisesRegex(ValueError,'confirmação'):svc.cadastrar_fixo_guiado(row,user)
        self.assertEqual(1,len(db.listar_compromissos()))

    def test_confirmacao_concorrente_cria_um_unico_fixo(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:svc.cadastrar_fixo_guiado(self.guided(),'teste'),range(2)))
        self.assertEqual(1,len({r['compromisso']['id'] for r in results}))
        self.assertEqual(1,len(db.listar_compromissos()))

    def test_tela_itau_mostra_dinheiro_do_banco_e_consolidado_distintos(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',100)
        db.definir_saldo_inicial_conta_mes('2026-09','Nubank',200)
        screen=self.exp._balance_account_screen('teste','Itaú','2026-09')
        self.assertIn('Dinheiro disponível neste banco: <b>R$ 100,00',screen.text)
        self.assertIn('Projeção consolidada de todas as contas: <b>R$ 300,00',screen.text)

    def test_telas_explicam_saldo_e_guia_sem_gravar(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',100)
        before=self.financial();s=self.exp.session('teste');s.month='2026-09'
        for screen in [self.exp.screen_home(s),self.exp.screen_balance(s),self.exp.screen_feature_guide(s)]:
            self.assertTrue(screen.rows)
            for row in screen.rows:
                for label,action in row:
                    if action[0]=='view':self.assertTrue(callable(getattr(self.exp,'screen_'+action[1],None)),label)
        self.assertEqual(before,self.financial())

    def test_backup_inclui_wal_e_preserva_original(self):
        source=Path(self.tmp.name)/'wal.db';dest=Path(self.tmp.name)/'backup.db'
        c=sqlite3.connect(source)
        self.addCleanup(c.close)
        c.execute('PRAGMA journal_mode=WAL');c.execute('CREATE TABLE exemplo (valor INTEGER)')
        c.execute('INSERT INTO exemplo VALUES (42)');c.commit()
        self.assertTrue(Path(str(source)+'-wal').exists())
        backup_sqlite_consistente(source,dest)
        with closing(sqlite3.connect(dest)) as copied:self.assertEqual(42,copied.execute('SELECT valor FROM exemplo').fetchone()[0])
        self.assertEqual(42,c.execute('SELECT valor FROM exemplo').fetchone()[0])

    def test_backup_nao_sobrescreve_destino_existente(self):
        dest=Path(self.tmp.name)/'backup.db';dest.write_text('preservar')
        with self.assertRaises(FileExistsError):backup_sqlite_consistente(self.path,dest)
        self.assertEqual('preservar',dest.read_text())


class ComposicaoSaldo(unittest.TestCase):
    def test_explicacao_inclui_saldo_e_compensacao_sem_mudar_calculo(self):
        s=resumir_saldo(dict(saldo_disponivel=1000,entradas_previstas=200,
            saidas_nao_imediatas_realizadas=300,despesas_esperadas_total=50,
            pendencias_herdadas_total=20,compensacao_pagamentos_fatura=100,
            saldo_projetado=930,resultado_projetado_mes=-70))
        self.assertEqual(270,s['reservas_liquidas']);self.assertEqual(930,s['saldo_final'])

    def test_centavos_exibidos_fecham_e_zero_nao_e_substituido(self):
        s=resumir_saldo(dict(saldo_disponivel=0.004,entradas_previstas=0.004,saldo_projetado=0.008))
        self.assertAlmostEqual(s['saldo_final'],s['saldo_atual']+s['a_receber']-s['reservas_liquidas'])
        self.assertEqual(0,resumir_saldo(dict(saldo_disponivel=100,despesas_esperadas_total=100,saldo_projetado=0))['saldo_final'])

    def test_divergencia_e_valor_nao_finito_nao_sao_ocultados(self):
        for row in [dict(saldo_disponivel=100,saldo_projetado=101),dict(saldo_projetado=float('nan'))]:
            with self.assertRaises(ValueError):resumir_saldo(row)
