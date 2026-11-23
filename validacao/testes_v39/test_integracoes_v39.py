"""Integracoes adicionais, concorrencia e reversao da V39."""
import csv
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from unittest.mock import patch

from testes_v39.test_v39 import Ambiente, dados, db, svc, comp, conc, ux, reg, fc, runner, ROOT


class IntegracoesV39(Ambiente):
    def compromisso(self, **kw):
        value=dict(tipo='fixo',nome='Mensalidade teste',categoria='Assinaturas',
                   conta_pagamento='Ita\u00fa',conta_origem='Ita\u00fa',
                   forma_pagamento='cr\u00e9dito',valor=150,dia_vencimento=10,
                   data_inicio='2026-09-01',ativo=True)
        value.update(kw)
        return db.inserir_compromisso(value)

    def test_handle_text_frase_completa_e_resposta(self):
        self.exp.handle_text(self.key,'gastei 150 no mercado credito itau em 25/09/2026')
        self.assertEqual('installment_choice',self.exp.session(self.key).stage)
        self.exp.handle_text(self.key,'não')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)
        self.exp.handle_text(self.key,'proximo mes')
        self.assertEqual('confirm',self.exp.session(self.key).stage)
        self.assertEqual('2026-10',self.exp.session(self.key).draft['competencia_fatura'])
        self.assertEqual(0,self.count())

    def test_dia31_preserva_ancora_apos_fevereiro(self):
        request=dados(data='2026-01-31',competencia_fatura='2026-02',parcelas_total=3)
        self.assertEqual(['2026-02-28','2026-03-31','2026-04-30'],
                         [x['data'].isoformat() for x in ux.installment_plan(request)])
        result=self.record(data='2026-01-31',competencia_fatura='2026-02',parcelas_total=3)
        self.assertEqual(['2026-02-28','2026-03-31','2026-04-30'],
                         [fc.data_competencia(x) for x in result['linhas']])
        self.assertTrue(all(x['data_compra']=='2026-01-31' for x in result['linhas']))

    def test_bissexto_29_fevereiro_tem_proxima_fatura(self):
        result=self.record(data='2028-02-29',competencia_fatura='2028-03',parcelas_total=2)
        self.assertEqual(['2028-03','2028-04'],[x['competencia_fatura'] for x in result['linhas']])
        self.assertEqual(0,self.invoice('2028-02')['valor_bruto'])

    def test_concorrencia_mesma_chave_cria_uma_compra(self):
        def run(_):return reg.confirmar_registro(dados(parcelas_total=3),'concorrente',self.key)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(run,range(4)))
        self.assertEqual(3,self.count())
        self.assertEqual(1,sum(not r['repetido'] for r in results))
        self.assertEqual(1,len({tuple(r['ids']) for r in results}))

    def test_concorrencia_compras_distintas_mesmo_valor_preservadas(self):
        def run(i):return reg.confirmar_registro(dados(),'compra-distinta-'+str(i),self.key)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(run,range(4)))
        self.assertEqual(4,self.count());self.assertEqual(600,self.invoice('2026-10')['valor_bruto'])

    def test_conciliacao_mes_da_fatura_mesmo_cartao(self):
        ident=self.compromisso()
        result=self.record(conciliacao=conc.alvo(ident,'2026-10'))
        self.assertEqual(1,len(conc.listar_vinculos()))
        self.assertEqual(150,self.invoice('2026-10')['valor_bruto'])
        self.assertEqual('2026-09-25',result['linhas'][0]['data'])
        self.assertEqual(150,self.invoice('2026-09')['valor_bruto'])

    def test_conciliacao_futura_outro_cartao_bloqueada_sem_registro_parcial(self):
        ident=self.compromisso(conta_pagamento='Nubank',conta_origem='Nubank')
        with self.assertRaises(conc.ConciliacaoError):self.record(conciliacao=conc.alvo(ident,'2026-10'))
        self.assertEqual(0,self.count());self.assertEqual([],conc.listar_vinculos())

    def test_conciliacao_mes_diferente_fatura_bloqueada(self):
        ident=self.compromisso()
        with self.assertRaises(conc.ConciliacaoError):self.record(conciliacao=conc.alvo(ident,'2026-09'))
        self.assertEqual(0,self.count())

    def test_conciliacao_nao_permite_antecipacao_pix(self):
        ident=self.compromisso(forma_pagamento='pix')
        request=dados(forma_pagamento='pix',conciliacao=conc.alvo(ident,'2026-10'))
        request.pop('competencia_fatura')
        with self.assertRaises(conc.ConciliacaoError):reg.confirmar_registro(request,'pix-futuro',self.key)
        self.assertEqual(0,self.count())

    def test_conciliacao_nao_aceita_parcelamento_automatico(self):
        ident=self.compromisso()
        with self.assertRaises(ValueError):self.record(parcelas_total=3,conciliacao=conc.alvo(ident,'2026-10'))
        self.assertEqual(0,self.count())

    def test_conciliacao_detecta_competencia_alterada_externamente(self):
        ident=self.compromisso();result=self.record(conciliacao=conc.alvo(ident,'2026-10'))
        with db.get_connection() as con:
            con.execute('UPDATE transacoes SET competencia_fatura=? WHERE id=?',('2026-11',result['ids'][0]))
        with self.assertRaises(conc.ConciliacaoError):conc.listar_vinculos()

    def test_desfazer_conciliacao_reabre_previsao_e_remove_compra(self):
        ident=self.compromisso();result=self.record(conciliacao=conc.alvo(ident,'2026-10'))
        self.assertTrue(reg.desfazer_registro('compra-1',self.key))
        self.assertEqual(0,self.count());self.assertEqual([],conc.listar_vinculos())
        self.assertEqual(150,self.invoice('2026-10')['valor_bruto'])

    def test_vincular_existente_abre_competencia_correta(self):
        ident=self.compromisso();result=self.record()
        screen=self.exp.begin_existing_link(self.key,result['ids'][0])
        self.assertEqual('2026-10',self.exp.session(self.key).month)
        self.assertIn('Outubro',screen.text)
        self.assertIn(str(ident),str(screen.rows))

    def test_vinculo_existente_revalida_metadados_da_previa(self):
        ident=self.compromisso();result=self.record();row=result['linhas'][0]
        expected=[row[k] for k in ('data','tipo','valor','conta','forma_pagamento')]
        with self.assertRaises(conc.ConciliacaoError):
            conc.vincular_existente(row['id'],conc.alvo(ident,'2026-10'),'link',self.key,
                expected,['2026-09-25','2026-09'])
        self.assertEqual([],conc.listar_vinculos())

    def test_exportacao_csv_mes_inclui_compra_e_competencia(self):
        self.record()
        with patch.object(svc,'EXPORTS_DIR',self.root/'exports'):
            result=svc.exportar_csv_mes('2026-10')
        self.assertIsInstance(result,dict)
        with open(result['arquivo'],encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream,delimiter=';'))
        self.assertEqual(1,len(rows));self.assertEqual(14,len(rows[0]))
        self.assertEqual('2026-09-25',rows[0]['data_compra'])
        self.assertEqual('2026-10',rows[0]['competencia_fatura'])
        self.assertEqual('150,00',rows[0]['valor'])

    def test_exportar_tudo_nao_omite_ultima_fatura(self):
        self.record(parcelas_total=3,valor=300)
        with patch.object(svc,'EXPORTS_DIR',self.root/'exports'):
            result=svc.exportar_csv_completo()
        self.assertIsInstance(result,dict)
        with open(result['arquivo'],encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream,delimiter=';'))
        self.assertEqual(['2026-10','2026-11','2026-12'],[x['competencia_fatura'] for x in rows])

    def test_exportacao_preserva_protecao_formula(self):
        self.record(descricao='=1+1')
        with patch.object(svc,'EXPORTS_DIR',self.root/'exports'):
            result=svc.exportar_csv_mes('2026-10')
        with open(result['arquivo'],encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream,delimiter=';'))
        self.assertEqual("'=1+1",rows[0]['nome'])

    def test_migracao4_sql_rollback_recusado_sem_perder_compra(self):
        self.record()
        with self.assertRaises(runner.MigrationError):
            runner.rollback(self.path,ROOT/'migrations',self.root/'backups',strategy='migration')
        self.assertEqual(1,self.count());self.assertEqual(150,self.invoice('2026-10')['valor_bruto'])

    def test_restore_backup_v3_e_copia_de_seguranca_v4(self):
        self.record()
        result=runner.rollback(self.path,ROOT/'migrations',self.root/'backups',strategy='backup')
        self.assertEqual(3,result['version_after'])
        self.assertTrue(Path(result['safety_backup']).exists())
        with db.get_connection() as con:
            self.assertEqual('ok',con.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertNotIn('competencia_fatura',{r[1] for r in con.execute('PRAGMA table_info(transacoes)')})
        self.assertEqual(0,self.count()) # Restaurar backup antigo descarta compras posteriores!

    def test_migration_status_validate_nao_alteram_banco(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        runner.get_status(self.path,ROOT/'migrations')
        self.assertTrue(runner.validate_compatibility(self.path,ROOT/'migrations',self.root/'backups').valid)
        runner.dry_run(self.path,ROOT/'migrations',self.root/'backups')
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_integridade_apos_gravar_editar_e_desfazer(self):
        result=self.record(parcelas_total=3)
        reg.desfazer_registro('compra-1',self.key)
        self.record()
        with db.get_connection() as con:
            self.assertEqual('ok',con.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertEqual([],list(con.execute('PRAGMA foreign_key_check')))

    def test_inicializacao_apos_migracao_preserva_registro_e_schema(self):
        result=self.record(parcelas_total=3)
        before=[dict(db.buscar_transacao_por_id(i)) for i in result['ids']]
        db.init_db() # Mesmo caminho chamado no inicio normal do bot.
        after=[dict(db.buscar_transacao_por_id(i)) for i in result['ids']]
        self.assertEqual(before,after)
        with db.get_connection() as con:
            self.assertEqual(4,con.execute('PRAGMA user_version').fetchone()[0])
        self.assertEqual(50,self.invoice('2026-10')['valor_bruto'])

    def test_falha_migration4_reverte_primeira_coluna(self):
        self.path=self.root/'migration_falha.db'
        db.DB_PATH=svc.DB_PATH=self.path
        db.init_db()
        historical=self.root/'historical';historical.mkdir()
        for source in (ROOT/'migrations').glob('[0-9][0-9][0-9][0-9]_*.py'):
            if int(source.name[:4])<=3:shutil.copy2(source,historical/source.name)
        runner.apply_migrations(self.path,historical,self.root/'backups_failure')
        migration=ROOT/'migrations/0004_competencia_faturas.py'
        content=migration.read_text(encoding='utf-8')
        content=content.replace('for statement in SQL:\n        connection.execute(statement)',
                               "for statement in SQL:\n        connection.execute(statement)\n        raise RuntimeError('Falha injetada apos primeiro ALTER')")
        (historical/migration.name).write_text(content,encoding='utf-8')
        with self.assertRaises(Exception):
            runner.apply_migrations(self.path,historical,self.root/'backups_failure')
        with db.get_connection() as con:
            self.assertEqual(3,con.execute('PRAGMA user_version').fetchone()[0])
            self.assertFalse({'data_compra','competencia_fatura'} & {r[1] for r in con.execute('PRAGMA table_info(transacoes)')})
            self.assertEqual(0,con.execute('SELECT count(*) FROM schema_migrations WHERE version=4').fetchone()[0])
            self.assertEqual('ok',con.execute('PRAGMA integrity_check').fetchone()[0])
