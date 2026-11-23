"""Onda 2C: números que se explicam entre telas, Histórico com transferências e faturas,
identidade (Painel, ids, voltar), alerta_valores, vazios e primeiro uso. Banco temporário, data fixa."""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 11, 9)


class Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 9)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / 'fixture.db'
        for target, field, value in ((db, 'DB_PATH', path), (svc, 'DB_PATH', path),
                                     (comp, 'date', Hoje), (svc, 'date', Hoje)):
            p = patch.object(target, field, value)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = 'onda2c'

    def act(self, *action):
        return self.engine.act(self.key, tuple(action))

    def fixo(self, nome, dia, valor, inicio='2026-11-01', conta='Itaú'):
        return db.inserir_compromisso(dict(
            tipo='fixo', nome=nome, categoria='Moradia', conta_pagamento=conta, forma_pagamento='pix',
            valor=valor, dia_vencimento=dia, data_inicio=inicio, data_fim=None, ativo=1, origem='teste'))

    def tx(self, desc='padaria', valor=45, conta='Itaú', dia='2026-11-08', tipo='despesa', forma='pix'):
        return db.inserir_transacao(dict(data=dia, tipo=tipo, valor=valor, categoria='Alimentação', descricao=desc,
                                         conta=conta, forma_pagamento=forma, parcelas_total=1))

    def internos(self):
        db.inserir_transferencia_caixa(dict(data='2026-11-07', valor=100, conta_origem='Itaú', conta_destino='Nubank',
                                            descricao='Transferência'))
        db.inserir_fatura_movimento(dict(ano_mes='2026-10', conta_cartao='Nubank', tipo_movimento='pagamento_total',
                                         valor=1300, data_movimento='2026-11-03', conta_origem='Itaú',
                                         descricao='Pagamento fatura Nubank'))

    @staticmethod
    def rotulos(tela):
        return [r for linha in tela.rows for r, _ in linha]

    @staticmethod
    def acoes(tela):
        return [a for linha in tela.rows for _, a in linha]


class NumerosQueSeExplicam(Base):
    def setUp(self):
        super().setUp()
        self.fixo('Academia', 20, 120, inicio='2026-10-01')  # outubro fica em aberto: atraso anterior
        self.fixo('Aluguel', 15, 1500)

    def test_a_pagar_diz_o_que_inclui_e_aponta_quanto_vou_pagar(self):
        tela = self.act('view', 'pay')
        self.assertIn('R$ 1.740,00', tela.text)
        self.assertIn('Inclui 1 conta de meses anteriores (R$ 120,00)', tela.text)
        self.assertIn('Quanto vou pagar mostra R$ 1.620,00', tela.text)
        self.assertIn('fixos no crédito já estão dentro', tela.text)
        self.assertIn(('pay_month', '2026-11', 0), self.acoes(tela))
        self.assertIn('Inclui 1 conta de meses anteriores', tela.rich_html)

    def test_quanto_vou_pagar_diz_o_que_exclui_e_aponta_a_pagar(self):
        tela = self.act('pay_month', '2026-11', 0)
        self.assertIn('TODAS AS CONTAS · R$ 1.620,00', tela.text)
        self.assertIn('Não inclui 1 conta de meses anteriores (R$ 120,00)', tela.text)
        self.assertIn('A pagar soma tudo: R$ 1.740,00', tela.text)
        self.assertIn('Não inclui 1 conta de meses anteriores', tela.rich_html)
        self.assertIn(('view', 'pay'), self.acoes(tela))

    def test_privacidade_mascara_as_linhas_de_explicacao(self):
        self.act('privacy')
        for tela in (self.act('view', 'pay'), self.act('pay_month', '2026-11', 0)):
            self.assertNotRegex(tela.text, r'R\$\s?\d')
            self.assertNotRegex(tela.rich_html or '', r'R\$\s?\d')
            self.assertIn('meses anteriores', tela.text)

    def test_filtro_explica_que_o_total_e_parcial(self):
        tela = self.act('filter', 'pay', 'overdue')
        self.assertIn('Total só dos itens deste filtro', tela.text)


class HistoricoComMovimentosInternos(Base):
    def setUp(self):
        super().setUp()
        self.tid = self.tx()
        self.internos()

    def test_transferencia_e_pagamento_de_fatura_aparecem_sem_contar_como_gasto(self):
        tela = self.act('view', 'history')
        self.assertTrue(tela.text.startswith('<b>📒 Histórico</b>'))
        self.assertIn('1 lançamento · 2 transferências e pagamentos de fatura', tela.text)
        self.assertIn('Transferência · R$ 100,00', tela.text)
        self.assertIn('Itaú → Nubank · não é gasto', tela.text)
        self.assertIn('Pagamento da fatura Nubank · R$ 1.300,00', tela.text)
        self.assertIn('fatura de Outubro 2026 · não é gasto', tela.text)
        # Só lançamentos reais têm botão (detalhe); os internos são linhas próprias.
        self.assertEqual([('transaction', self.tid)], [a for a in self.acoes(tela) if a[0] == 'transaction'])

    def test_filtros_despesa_e_interno(self):
        despesas = self.act('filter', 'history', 'despesa')
        self.assertNotIn('Transferência', despesas.text)
        internos = self.act('filter', 'history', 'interno')
        self.assertIn('Transferência · R$ 100,00', internos.text)
        self.assertNotIn('padaria', internos.text)
        self.assertIn('Filtro: transferências e faturas', internos.text)
        ferramentas = self.act('history_tools')
        self.assertIn(('filter', 'history', 'interno'), self.acoes(ferramentas))

    def test_ver_movimentos_da_conta_abre_o_historico_com_a_conta(self):
        detalhe = self.act('cash_account_detail', 'Itaú', '2026-11')
        self.assertIn(('account_history', 'Itaú', '2026-11'), self.acoes(detalhe))
        self.assertNotIn('legacy_raw', [a[0] for a in self.acoes(detalhe)])
        tela = self.act('account_history', 'Itaú', '2026-11')
        self.assertIn('padaria', tela.text)
        self.assertIn('Transferência · R$ 100,00', tela.text)
        self.assertIn('Pagamento da fatura Nubank', tela.text)
        nubank = self.act('account_history', 'Nubank', '2026-11')
        self.assertNotIn('padaria', nubank.text)
        self.assertIn('Transferência · R$ 100,00', nubank.text)

    def test_privacidade_no_historico(self):
        self.act('privacy')
        tela = self.act('view', 'history')
        self.assertNotRegex(tela.text, r'R\$\s?\d')
        self.assertIn('Transferência', tela.text)


class IdentidadeConsistente(Base):
    def test_ids_internos_fora_do_texto_principal(self):
        tid = self.tx()
        historico = self.act('view', 'history')
        self.assertFalse([r for r in self.rotulos(historico) if r.startswith('#')])
        self.assertIn('1. padaria', self.rotulos(historico))
        detalhe = self.act('transaction', tid)
        principal = '\n'.join(l for l in detalhe.text.splitlines() if 'Código para comandos de texto' not in l)
        self.assertNotRegex(principal, r'#\d')
        self.assertTrue(detalhe.text.rstrip().endswith(f'<i>Código para comandos de texto: #{tid}</i>'))

    def test_painel_no_lugar_de_dashboard(self):
        self.tx()
        telas = [self.act('view', 'month_actions'), self.act('view', 'review_tools'), self.act('pay_tools'),
                 self.act('innovations'), self.act('topic', 'dashboard')]
        for tela in telas:
            self.assertNotIn('Dashboard', ' '.join(self.rotulos(tela)))
            self.assertNotIn('Dashboard', tela.text)
            self.assertNotIn('Painel visual', ' '.join(self.rotulos(tela)))
        self.assertIn('📊 Painel', self.rotulos(telas[0]))
        # "dashboard" digitado continua aceito como sinônimo.
        self.assertIsNotNone(self.engine.handle_text(self.key, 'dashboard').image)
        self.assertIsNotNone(self.engine.handle_text(self.key, 'painel').image)

    def test_voltar_no_padrao(self):
        self.tx()
        for acao in (('view', 'categories'), ('history_tools',), ('pay_tools',), ('period_tools',),
                     ('view', 'planning_tools'), ('view', 'data_tools'), ('topic', 'saldo'), ('view', 'alert_settings')):
            tela = self.act(*acao)
            rotulos = self.rotulos(tela)
            self.assertIn('↩ Voltar', rotulos, acao)
            self.assertFalse([r for r in rotulos if r.startswith(('←', '‹ Mais', '‹ Meus'))], acao)
            self.assertEqual(1, sum(r == '↩ Voltar' for r in rotulos), acao)
            self.assertNotIn('Meu mês', ' '.join(rotulos))

    def test_data_br_e_saldo_que_diverge_da_soma_por_conta(self):
        self.assertEqual('10/11/2026', ux.data_br('2026-11-10'))
        self.assertEqual('', ux.data_br(None))
        # Lançamento sem banco definido: entra no Saldo consolidado, mas não em nenhuma conta.
        self.tx(desc='salário', valor=500, conta='', tipo='receita')
        saldo = self.act('view', 'balance')
        if 'Saldos por conta somam' in saldo.text:
            self.assertIn('Confira em Por conta', saldo.text)


class AlertaValores(Base):
    def test_botao_alterna_preferencia_com_aviso_de_tela_bloqueada(self):
        tela = self.act('view', 'alert_settings')
        self.assertIn('Incluir valores nos avisos: não', tela.text)
        self.assertIn('tela bloqueada', tela.text)
        self.assertIn('só saem quando há algo a dizer', tela.text)
        self.assertNotIn('⚠️', tela.text)
        self.assertIn(('pref', 'alerta_valores', True), self.acoes(tela))
        depois = self.act('pref', 'alerta_valores', True)
        self.assertIn('Incluir valores nos avisos: sim', depois.text)
        self.assertIn(('pref', 'alerta_valores', False), self.acoes(depois))
        import assessor_orientacao as orient
        self.assertTrue(orient.preferencias(self.key)['alerta_valores'])
        alertas = self.act('view', 'alerts')
        self.assertIn('Valores nos avisos: incluídos', alertas.text)
        self.assertIn('O aviso da noite só sai quando há algo a dizer', alertas.text)

    def test_pausa_em_data_brasileira(self):
        self.act('pref', 'pausa_ate', '2026-11-10')
        tela = self.act('view', 'alert_settings')
        self.assertIn('Pausa até 10/11/2026', tela.text)
        self.assertNotRegex(tela.text, r'\d{4}-\d{2}-\d{2}')


class VaziosEPrimeiroUso(Base):
    def test_primeiro_uso_conduz_saldos_registro_inicio(self):
        inicio = self.act('view', 'home')
        self.assertIn('Primeiros passos', inicio.text)
        self.assertEqual(('🚀 1. Informar saldos', ('cash_setup_start',)), inicio.rows[0][0])
        texto, botao = self.engine._primeiro_uso({'base_configurada': True})
        self.assertIn('Próximo passo', texto)
        self.assertEqual(('view', 'register'), botao[1])
        self.tx()
        self.assertEqual((None, None), self.engine._primeiro_uso({'base_configurada': True}))
        self.assertNotIn('Primeiros passos', self.act('view', 'home').text)

    def test_com_fixos_cadastrados_nao_e_primeiro_uso(self):
        self.fixo('Aluguel', 5, 1500)
        self.assertNotIn('Primeiros passos', self.act('view', 'home').text)

    def test_telas_vazias_convidam_com_um_botao(self):
        casos = {('view', 'pay'): ('new_fixed_start',), ('view', 'history'): ('view', 'register'),
                 ('view', 'categories'): ('start', 'despesa'), ('view', 'accounts_manage'): ('cash_setup_new_account',)}
        for acao, esperado in casos.items():
            tela = self.act(*acao)
            self.assertIn(esperado, self.acoes(tela), acao)
            self.assertNotIn('Nada encontrado', tela.text)
        fixos = self.act('fixed_list', 0)
        self.assertIn('Nenhum fixo cadastrado ainda', fixos.text)
        self.assertIn(('new_fixed_start',), self.acoes(fixos))
        limites = self.act('view', 'budgets')
        self.assertIn('Nenhum limite definido ainda', limites.text)
        self.assertIn(('budget_start',), self.acoes(limites))


if __name__ == '__main__':
    unittest.main()
