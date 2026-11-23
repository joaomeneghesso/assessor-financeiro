"""Bloco C: ciclo de vida de registros, parcelamentos e fixos.

C1 Desfazer recusa quando algo gravado depois depende do registro
   (pagamento/ajuste da mesma fatura; "saldo atual" da mesma conta e mês).
C2 Exclusão por ID/faixa/último não leva só parte de um parcelamento;
   corrigir o valor de uma parcela mantém o total do parcelamento coerente.
C3 Versão de fixo com histórico (série de "nova condição") e meses passados
   não é apagada; apagar um compromisso limpa as linhas do checklist dele.
C4 Nova condição de fixo é permitida quando todas as conciliações são de
   meses anteriores ao novo mês (a versão antiga as mantém).
Cada bloco também confere que o comportamento anterior continua igual.
"""
import importlib.util
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import compromissos as comp
import conciliacao as conc
import database as db
import fixos_edicao as fx
import saldos_edicao
import services as svc
import telegram_registros as reg
from tests.relogio_fixo import data_fixa

_spec = importlib.util.spec_from_file_location('migration_runner_bloco_c', ROOT / 'migrations.py')
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)

SESSAO = {'user_id': 1, 'chat_id': 1}



class _ConexaoQueFecha(sqlite3.Connection):
    """Como `with conn`, mas também fecha: no Windows uma conexão aberta
    impede apagar o banco temporário no fim do teste."""
    def __exit__(self, *exc):
        try:
            return super().__exit__(*exc)
        finally:
            self.close()

class Today(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 30)


class Now(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 30, 12, 0, tzinfo=tz)


def compra(**kw):
    dados = dict(data='2026-09-25', tipo='despesa', valor=150.0, categoria='Alimentação',
                 descricao='Mercado teste', conta='Itaú', forma_pagamento='crédito',
                 parcelas_total=1, competencia_fatura='2026-10')
    dados.update(kw)
    return dados


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.path = root / 'financeiro.db'
        for p in (patch.object(db, 'DB_PATH', self.path), patch.object(svc, 'DB_PATH', self.path),
                  patch.object(svc, 'BACKUPS_DIR', root / 'backups'),
                  patch.object(svc, 'date', Today), patch.object(comp, 'date', Today),
                  patch.object(conc, 'datetime', Now),
                  patch.dict(os.environ, {'ASSESSOR_FATURA_DIA_CORTE': '25', 'ASSESSOR_FATURA_CORTES': '{}'})):
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        runner.apply_migrations(self.path, ROOT / 'migrations', root / 'mig_backups', executed_by='bloco_c')
        svc.cancelar_exclusao_pendente(SESSAO)
        self.counter = 0

    def q(self, sql, *args):
        with sqlite3.connect(self.path, factory=_ConexaoQueFecha) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute(sql, args)]

    def run_cmd(self, texto):
        return str(svc.processar_mensagem(texto, sessao=SESSAO))

    def snapshot(self):
        tabelas = ('transacoes', 'compromissos', 'fatura_movimentos', 'saldos_mensais_contas',
                   'checklist_pagamentos', 'checklist_datas_pagamento', 'checklist_datas_pagamento_padrao')
        return {t: self.q(f'SELECT * FROM {t} ORDER BY id') for t in tabelas}


class C1DesfazerComDependencia(Base):
    usuario = 'usuario-c1'

    def registrar(self, **kw):
        self.counter += 1
        chave = 'reg-' + str(self.counter)
        reg.confirmar_registro(compra(**kw), chave, self.usuario)
        return chave

    def fatura(self, mes='2026-10', conta='Itaú'):
        return comp.calcular_fatura_unificada(mes, conta, somente_cartao=True)

    def pagar_total(self, mes='2026-10', conta='Itaú', chave='pg-1'):
        saldo = round(self.fatura(mes, conta)['saldo_restante'], 2)
        return reg.confirmar_pagamento_fatura(dict(ano_mes=mes, conta_cartao=conta, conta_origem='BTG',
                                                   modo='total', valor=saldo, saldo_esperado=saldo,
                                                   data_movimento='2026-09-30'), chave, self.usuario)

    def desfeitos(self):
        return self.q("SELECT id FROM auditoria_eventos WHERE entidade='telegram_registro' AND operacao='desfeito'")

    def test_pagamento_posterior_da_fatura_bloqueia_desfazer(self):
        chave = self.registrar()
        self.pagar_total()
        antes = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'fatura dessa compra recebeu pagamento'):
            reg.desfazer_registro(chave, self.usuario)
        self.assertEqual(antes, self.snapshot())
        self.assertEqual([], self.desfeitos())
        self.assertAlmostEqual(0.0, self.fatura()['saldo_restante'], places=2)

    def test_pagamento_de_outra_fatura_ou_anterior_nao_bloqueia(self):
        # Pagamento de outro cartão e de outra competência depois do registro.
        db.inserir_fatura_movimento(dict(ano_mes='2026-10', conta_cartao='Nubank', tipo_movimento='pagamento_parcial',
                                         valor=10, data_movimento='2026-09-30', conta_origem='BTG'))
        chave = self.registrar()
        db.inserir_fatura_movimento(dict(ano_mes='2026-10', conta_cartao='Nubank', tipo_movimento='pagamento_parcial',
                                         valor=10, data_movimento='2026-09-30', conta_origem='BTG'))
        db.inserir_fatura_movimento(dict(ano_mes='2026-11', conta_cartao='Itaú', tipo_movimento='pagamento_parcial',
                                         valor=10, data_movimento='2026-09-30', conta_origem='BTG'))
        self.assertTrue(reg.desfazer_registro(chave, self.usuario))
        self.assertFalse(reg.desfazer_registro(chave, self.usuario))
        self.assertEqual(0, self.q('SELECT count(*) n FROM transacoes')[0]['n'])

    def test_pagamento_gravado_antes_do_registro_nao_bloqueia(self):
        mov = db.inserir_fatura_movimento(dict(ano_mes='2026-10', conta_cartao='Itaú', tipo_movimento='pagamento_parcial',
                                               valor=10, data_movimento='2026-09-20', conta_origem='BTG'))
        with sqlite3.connect(self.path, factory=_ConexaoQueFecha) as c:
            c.execute("UPDATE fatura_movimentos SET criado_em='2026-09-20T10:00:00', atualizado_em='2026-09-20T10:00:00' WHERE id=?", (mov,))
        chave = self.registrar()
        self.assertTrue(reg.desfazer_registro(chave, self.usuario))

    def test_parcelamento_bloqueia_so_quando_a_competencia_da_parcela_foi_paga(self):
        chave = self.registrar(valor=300.0, parcelas_total=3)
        self.pagar_total(mes='2026-11')
        with self.assertRaises(ValueError):
            reg.desfazer_registro(chave, self.usuario)
        self.assertEqual(3, self.q('SELECT count(*) n FROM transacoes')[0]['n'])

    def test_parcelamento_inteiro_ainda_pode_ser_desfeito(self):
        chave = self.registrar(valor=300.0, parcelas_total=3)
        self.assertTrue(reg.desfazer_registro(chave, self.usuario))
        self.assertEqual(0, self.q('SELECT count(*) n FROM transacoes')[0]['n'])

    def test_saldo_atual_posterior_da_mesma_conta_e_mes_bloqueia(self):
        chave = self.registrar(forma_pagamento='pix', competencia_fatura=None)
        saldos_edicao.confirmar('2026-09', 'Itaú', '1000', saldos_edicao.capturar('2026-09'), 'outra-sessao')
        antes = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'saldo atual dessa conta foi ajustado'):
            reg.desfazer_registro(chave, self.usuario)
        self.assertEqual(antes, self.snapshot())
        self.assertEqual([], self.desfeitos())

    def test_saldo_atual_de_outra_conta_ou_outro_mes_nao_bloqueia(self):
        chave = self.registrar(forma_pagamento='pix', competencia_fatura=None)
        saldos_edicao.confirmar('2026-09', 'BTG', '500', saldos_edicao.capturar('2026-09'), 'outra-sessao')
        saldos_edicao.confirmar('2026-10', 'Itaú', '700', saldos_edicao.capturar('2026-10'), 'outra-sessao')
        self.assertTrue(reg.desfazer_registro(chave, self.usuario))

    def test_saldo_atual_anterior_ao_registro_nao_bloqueia(self):
        saldos_edicao.confirmar('2026-09', 'Itaú', '1000', saldos_edicao.capturar('2026-09'), 'outra-sessao')
        chave = self.registrar(forma_pagamento='pix', competencia_fatura=None)
        self.assertTrue(reg.desfazer_registro(chave, self.usuario))

    def test_preservado_edicao_e_sessao(self):
        chave = self.registrar()
        with self.assertRaises(ValueError):
            reg.desfazer_registro(chave, 'outra-sessao')
        with sqlite3.connect(self.path, factory=_ConexaoQueFecha) as c:
            c.execute("UPDATE transacoes SET valor=1")
        with self.assertRaisesRegex(ValueError, 'foi alterado'):
            reg.desfazer_registro(chave, self.usuario)


class C2ParcelamentoParcial(Base):
    def parcelado(self, valor=300, n=3):
        svc.registrar_compra_parcelada(dict(data='2026-09-10', tipo='despesa', valor=valor, categoria='Compras',
                                            descricao='Notebook', conta='Itaú', forma_pagamento='crédito',
                                            parcelas_total=n, mensagem_original='teste'))
        return [r['id'] for r in self.q('SELECT id FROM transacoes ORDER BY id')][-n:]

    def avulso(self, descricao='Padaria'):
        return db.inserir_transacao(dict(data='2026-09-10', tipo='despesa', valor=10, categoria='Alimentação',
                                         descricao=descricao, conta='Itaú', forma_pagamento='pix',
                                         mensagem_original='teste'))

    def assert_recusa(self, comando):
        antes = self.snapshot()
        previa = self.run_cmd(comando)
        self.assertTrue(previa.startswith(svc.PREFIXO_EXCLUSAO_PARCIAL_PARCELAMENTO), previa)
        self.assertIn('Nada foi apagado', previa)
        self.assertIn('apagar parcelamento P', previa)
        self.assertNotIn('confirmar exclusao', previa)
        self.assertIn('Não há exclusão pendente', self.run_cmd('confirmar exclusao'))
        # Execução direta (caminho já confirmado) também recusa, sem apagar.
        executado = str(svc.executar_exclusao_confirmada(comando, sessao=SESSAO))
        self.assertTrue(executado.startswith(svc.PREFIXO_EXCLUSAO_PARCIAL_PARCELAMENTO), executado)
        self.assertEqual(antes, self.snapshot())

    def test_apagar_uma_parcela_ou_faixa_parcial_recusa(self):
        antes_id = self.avulso()
        ids = self.parcelado()
        self.assert_recusa(f'apagar {ids[0]}')
        self.assert_recusa(f'apagar {ids[1]}')
        self.assert_recusa(f'apagar {antes_id}-{ids[1]}')
        self.assert_recusa('apagar último')

    def test_faixa_com_parcelamento_inteiro_e_avulsos_segue_igual(self):
        a = self.avulso()
        self.parcelado()
        b = self.avulso('Farmácia')
        previa = self.run_cmd(f'apagar {a}-{b}')
        self.assertIn('Você está prestes a apagar 5 lançamento(s)', previa)
        self.assertIn('Transações apagadas em faixa', self.run_cmd('confirmar exclusao'))
        self.assertEqual([], self.q('SELECT id FROM transacoes'))

    def test_avulso_e_parcelamento_inteiro_seguem_iguais(self):
        a = self.avulso()
        ids = self.parcelado()
        self.assertIn('Você está prestes a apagar este lançamento', self.run_cmd(f'apagar {a}'))
        self.assertIn('Transação apagada', self.run_cmd('confirmar exclusao'))
        self.run_cmd(f'apagar parcelamento P{ids[0]}')
        self.assertIn('Parcelas apagadas: 3/3', self.run_cmd('confirmar exclusao'))
        self.assertEqual([], self.q('SELECT id FROM transacoes'))

    def test_corrigir_valor_de_parcela_atualiza_total_do_parcelamento(self):
        ids = self.parcelado()
        self.assertIn('Responda: confirmar alteracao', self.run_cmd(f'corrigir valor {ids[1]} para 150'))
        resposta = self.run_cmd('confirmar alteracao')  # Onda 1: prévia + confirmação
        self.assertIn('Valor atualizado', resposta)
        self.assertIn(f'Total do parcelamento P{ids[0]} atualizado para R$ 350,00', resposta)
        linhas = self.q('SELECT valor, valor_total_parcelamento FROM transacoes ORDER BY id')
        self.assertEqual([100.0, 150.0, 100.0], [r['valor'] for r in linhas])
        self.assertEqual({350.0}, {r['valor_total_parcelamento'] for r in linhas})
        self.assertIn('R$ 350,00', svc.detalhar_parcelamento(ids[0]))

    def test_corrigir_valor_de_avulso_segue_igual(self):
        a = self.avulso()
        self.assertIn('Responda: confirmar alteracao', self.run_cmd(f'corrigir valor {a} para 12,50'))
        resposta = self.run_cmd('confirmar alteracao')  # Onda 1: prévia + confirmação
        self.assertIn('Valor atualizado', resposta)
        self.assertNotIn('Total do parcelamento', resposta)
        self.assertEqual(12.5, self.q('SELECT valor FROM transacoes WHERE id=?', a)[0]['valor'])


class C3ApagarFixo(Base):
    def fixo(self, **kw):
        row = dict(tipo='fixo', nome='Plano de celular', categoria='Telefonia', conta_pagamento='Itaú',
                   forma_pagamento='pix', valor=49.99, dia_vencimento=10, data_inicio='2026-01-01',
                   data_fim=None, ativo=True, origem='teste')
        row.update(kw)
        return db.inserir_compromisso(row)

    def nova_condicao(self, ident, valor, mes):
        return fx.salvar(fx.preparar(ident, 'valor', valor, mes), 'sessao-teste')

    def novo_id(self):
        return max(r['id'] for r in self.q('SELECT id FROM compromissos'))

    def test_versao_antiga_e_atual_com_passado_nao_sao_apagadas(self):
        # "passado"/"futuro" da série dependem de hoje: fixa o dia.
        self.enterContext(data_fixa(date(2026, 11, 9)))
        hoje = date.today()
        mes_passado = (hoje.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        old = self.fixo(data_inicio=f'{hoje.year - 2}-01-01')
        self.nova_condicao(old, '59,99', mes_passado)
        new = self.novo_id()
        for ident in (old, new):
            antes = self.snapshot()
            previa = self.run_cmd(f'apagar fixo {ident}')
            self.assertTrue(previa.startswith(db.PREFIXO_EXCLUSAO_FIXO_SERIE), previa)
            self.assertIn('Nada foi apagado', previa)
            self.assertIn('Não há exclusão pendente', self.run_cmd('confirmar exclusao'))
            self.assertTrue(str(svc.executar_exclusao_confirmada(f'apagar fixo {ident}', sessao=SESSAO))
                            .startswith(db.PREFIXO_EXCLUSAO_FIXO_SERIE))
            self.assertEqual(antes, self.snapshot())
        self.assertIn('pausar fixo', self.run_cmd(f'apagar fixo {new}'))
        self.assertIn('já está encerrada', self.run_cmd(f'apagar fixo {old}'))
        self.assertEqual([old], [i['id'] for i in comp.projetar_compromissos_mes(f'{hoje.year - 2}-03')
                                 if i['nome'] == 'Plano de celular'])

    def test_versao_so_futura_e_fixo_sem_serie_seguem_apagaveis(self):
        self.enterContext(data_fixa(date(2026, 11, 9)))
        hoje = date.today()
        futuro = f'{hoje.year + 2}-01'
        old = self.fixo(data_inicio=f'{hoje.year + 1}-01-01')
        self.nova_condicao(old, '59,99', futuro)
        new = self.novo_id()
        self.assertIn('Você está prestes a apagar este compromisso', self.run_cmd(f'apagar fixo {new}'))
        self.assertIn('Compromisso apagado', self.run_cmd('confirmar exclusao'))
        sozinho = self.fixo(nome='Internet')
        self.assertIn('Você está prestes a apagar este compromisso', self.run_cmd(f'apagar fixo {sozinho}'))
        self.assertIn('Compromisso apagado', self.run_cmd('confirmar exclusao'))

    def test_apagar_compromisso_remove_linhas_do_checklist_dele(self):
        alvo = self.fixo(nome='Tag condomínio', tipo='avulso', data_inicio='2026-06-10', data_fim='2026-06-10')
        outro = self.fixo(nome='Internet')
        agora = '2026-06-25T10:00:00'
        with sqlite3.connect(self.path, factory=_ConexaoQueFecha) as c:
            for chave in (f'C{alvo}', f'P{alvo}', f'C{outro}'):
                c.execute('INSERT INTO checklist_pagamentos (ano_mes,item_chave,status,pago_em,criado_em,atualizado_em) '
                          'VALUES (?,?,?,?,?,?)', ('2026-06', chave, 'pago', agora, agora, agora))
                c.execute('INSERT INTO checklist_datas_pagamento (ano_mes,item_chave,data_pagamento,criado_em,atualizado_em) '
                          'VALUES (?,?,?,?,?)', ('2026-06', chave, '2026-06-10', agora, agora))
                c.execute('INSERT INTO checklist_datas_pagamento_padrao (item_chave,dia_pagamento,criado_em,atualizado_em) '
                          'VALUES (?,?,?,?)', (chave, 10, agora, agora))
        self.run_cmd(f'apagar fixo {alvo}')
        self.assertIn('Compromisso apagado', self.run_cmd('confirmar exclusao'))
        for tabela in ('checklist_pagamentos', 'checklist_datas_pagamento', 'checklist_datas_pagamento_padrao'):
            self.assertEqual([f'C{outro}'], [r['item_chave'] for r in self.q(f'SELECT item_chave FROM {tabela}')])

    def test_bloqueio_por_conciliacao_preservado(self):
        ident = self.fixo(nome='Internet')
        tid = db.inserir_transacao(dict(data='2026-09-10', tipo='despesa', valor=49.99, categoria='Telefonia',
                                        descricao='Internet', conta='Itaú', forma_pagamento='pix',
                                        mensagem_original='teste'))
        with db.fatura_write_transaction() as conn:
            conc.vincular_conn(conn, tid, conc.alvo(ident, '2026-09'), 'vinc-c3', 'usuario')
        self.run_cmd(f'apagar fixo {ident}')
        self.assertIn('Compromisso com conciliações', self.run_cmd('confirmar exclusao'))
        self.assertEqual(1, len(self.q('SELECT id FROM compromissos WHERE id=?', ident)))


class C4NovaCondicaoComConciliacao(Base):
    def setUp(self):
        super().setUp()
        self.ident = db.inserir_compromisso(dict(tipo='fixo', nome='Condomínio', categoria='Moradia',
                                                 conta_pagamento='Itaú', forma_pagamento='pix', valor=200.0,
                                                 dia_vencimento=10, data_inicio='2026-06-01', data_fim=None,
                                                 ativo=True, origem='teste'))
        self.tid = db.inserir_transacao(dict(data='2026-09-10', tipo='despesa', valor=200.0, categoria='Moradia',
                                             descricao='Condomínio', conta='Itaú', forma_pagamento='pix',
                                             mensagem_original='teste'))
        alvo = conc.alvo(self.ident, '2026-09')
        with db.fatura_write_transaction() as conn:
            conc.vincular_conn(conn, self.tid, alvo, 'vinc-1', 'usuario')

    def test_nova_condicao_depois_das_conciliacoes_e_permitida_e_mantem_vinculo(self):
        resposta = fx.salvar(fx.preparar(self.ident, 'valor', '250', '2026-10'), 's')
        self.assertIn('Nova condição a partir de Outubro 2026', resposta)
        old = db.buscar_compromisso_por_id(self.ident)
        self.assertEqual('2026-09-30', old['data_fim'])
        vinculos = conc.listar_vinculos()
        self.assertEqual([(self.ident, '2026-09', self.tid)], [(v['compromisso_id'], v['mes'], v['transacao_id']) for v in vinculos])
        setembro = [i for i in comp.projetar_compromissos_mes('2026-09') if i['nome'] == 'Condomínio']
        self.assertEqual([(self.ident, 0.0, True)], [(i['id'], i['valor'], i.get('conciliado')) for i in setembro])
        outubro = [i for i in comp.projetar_compromissos_mes('2026-10') if i['nome'] == 'Condomínio']
        self.assertEqual([250.0], [i['valor'] for i in outubro])
        self.assertNotEqual(self.ident, outubro[0]['id'])

    def test_conciliacao_no_mes_da_nova_condicao_ou_depois_bloqueia(self):
        antes = self.snapshot()
        with self.assertRaisesRegex(conc.ConciliacaoError, 'conciliações em Setembro 2026 ou depois'):
            fx.salvar(fx.preparar(self.ident, 'valor', '250', '2026-09'), 's')
        self.assertEqual(antes, self.snapshot())

    def test_correcao_sem_mes_continua_bloqueada(self):
        with self.assertRaisesRegex(conc.ConciliacaoError, 'Compromisso com conciliações'):
            fx.salvar(fx.preparar(self.ident, 'valor', '250'), 's')
        self.assertIn('Fixo atualizado', fx.salvar(fx.preparar(self.ident, 'nome', 'Condomínio Novo'), 's'))


if __name__ == '__main__':
    unittest.main()
