"""Fase 2 (P3, P4, P7): registro guiado mais curto, sempre com confirmação."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import sugestoes_lancamento as sug
import telegram_experiencia as ux

HOJE = date(2026, 9, 20)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = 'rapido-f2'

    def tx(self, desc, forma='débito', conta='Itaú', dia='2026-09-10', valor=40, cat='Mercado',
           tipo='despesa', parcelas=1):
        return db.inserir_transacao(dict(data=dia, tipo=tipo, valor=valor, categoria=cat, descricao=desc,
                                         conta=conta, forma_pagamento=forma, parcelas_total=parcelas))

    def count(self):
        with db.get_connection() as c:
            return c.execute('SELECT count(*) FROM transacoes').fetchone()[0]

    def acoes(self, screen, kind):
        return [tuple(a) for row in screen.rows for _, a in row if a and a[0] == kind]

    def stage(self):
        return self.engine.session(self.key).stage


class SugestoesPorHistorico(Base):
    def test_historico_coerente_leva_direto_ao_cartao_com_marca(self):
        for dia in ('2026-09-01', '2026-09-08', '2026-09-15'):
            self.tx('mercado', dia=dia)
        antes = self.count()
        screen = self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.assertEqual('confirm', self.stage())
        self.assertIn('✦', screen.text)
        self.assertIn('sugerido pelo seu histórico', screen.text)
        self.assertEqual(antes, self.count())  # sugerir nunca grava
        draft = self.engine.session(self.key).draft
        self.assertEqual('Itaú', draft['conta'])
        self.assertEqual('débito', draft['forma_pagamento'])
        self.assertEqual(HOJE.isoformat(), draft['data'])
        # editáveis por toque
        self.assertTrue(self.acoes(screen, 'edit'))
        # 2 ações: a frase e Salvar
        commit = self.acoes(screen, 'commit')[0]
        self.engine.act(self.key, commit)
        self.assertEqual(antes + 1, self.count())
        with db.get_connection() as c:
            row = c.execute('SELECT conta, forma_pagamento, data, mensagem_original FROM transacoes ORDER BY id DESC').fetchone()
        self.assertEqual(('Itaú', 'débito', HOJE.isoformat()), tuple(row[:3]))
        self.assertNotIn('_sugerido', str(row[3]))
        # idempotência do commit inalterada
        again = self.engine.act(self.key, commit)
        self.assertEqual(antes + 1, self.count())
        self.assertIn('expirou', again.text)

    def test_payload_gravavel_nao_leva_chaves_de_sugestao(self):
        for dia in ('2026-09-01', '2026-09-08'):
            self.tx('mercado', dia=dia)
        self.engine.handle_text(self.key, 'gastei 45 no mercado')
        draft = self.engine.session(self.key).draft
        self.assertIn('_sugerido', draft)
        payload = self.engine.payload(draft)
        self.assertFalse([k for k in payload if k.startswith('_')])

    def test_uma_ocorrencia_nao_sugere(self):
        self.tx('mercado')
        self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.assertEqual('method', self.stage())
        self.assertNotIn('_sugerido', self.engine.session(self.key).draft)

    def test_historico_dividido_nao_sugere(self):
        self.tx('mercado', conta='Itaú', forma='débito', dia='2026-09-01')
        self.tx('mercado', conta='Nubank', forma='crédito', dia='2026-09-02')
        self.tx('mercado', conta='Itaú', forma='débito', dia='2026-09-03')
        self.tx('mercado', conta='Nubank', forma='crédito', dia='2026-09-04')
        self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.assertEqual('method', self.stage())

    def test_sem_historico_pergunta_forma_conta_e_nao_parcelas_nem_data(self):
        screen = self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.assertEqual('method', self.stage())
        self.assertNotIn('parcelada', screen.text)
        screen = self.engine.act(self.key, ('answer', 'pix'))
        self.assertEqual('account', self.stage())
        screen = self.engine.handle_text(self.key, 'Itaú')
        self.assertEqual('confirm', self.stage())  # sem etapa de data
        self.assertTrue(self.acoes(screen, 'commit'))
        self.assertNotIn('✦', screen.text)

    def test_pix_nunca_vira_conta_e_fatura_fica_fora(self):
        self.tx('mercado', conta='Pix', forma='pix', dia='2026-09-01')
        self.tx('mercado', conta='Pix', forma='pix', dia='2026-09-02')
        self.tx('pagamento fatura nubank', conta='Itaú', forma='pix', cat='Pagamento de fatura')
        self.tx('pagamento fatura nubank', conta='Itaú', forma='pix', cat='Pagamento de fatura')
        self.assertNotIn('conta', sug.sugerir('mercado', 'despesa'))
        self.assertEqual({}, sug.sugerir('pagamento fatura nubank', 'despesa'))

    def test_credito_pos_corte_continua_pedindo_o_mes_sem_perguntar_parcelas(self):
        engine = ux.Experience(date_provider=lambda: date(2026, 9, 30))
        for dia in ('2026-08-01', '2026-08-08'):
            self.tx('farmácia', conta='Nubank', forma='crédito', dia=dia, cat='Saúde')
        screen = engine.handle_text(self.key, 'gastei 45 na farmácia')
        self.assertEqual('billing_month', engine.session(self.key).stage)
        self.assertNotIn('parcelada', screen.text)
        self.assertEqual(0, self.count() - 2)

    def test_editar_campo_sugerido_remove_a_marca(self):
        for dia in ('2026-09-01', '2026-09-08'):
            self.tx('mercado', dia=dia)
        self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.engine.act(self.key, ('edit', 'method'))
        screen = self.engine.act(self.key, ('answer', 'pix'))
        draft = self.engine.session(self.key).draft
        self.assertNotIn('forma_pagamento', draft['_sugerido'])
        self.assertEqual('pix', draft['forma_pagamento'])
        self.assertEqual('confirm', self.stage())


class PerguntasCertas(Base):
    def test_botoes_debito_sem_parcelas_e_sem_data(self):
        screen = self.engine.act(self.key, ('start', 'despesa'))
        self.assertEqual('amount', self.stage())
        self.assertNotIn('parcelada', screen.text)
        self.engine.handle_text(self.key, '35,90')
        self.engine.handle_text(self.key, 'almoço')
        self.engine.act(self.key, ('answer', 'débito'))
        self.assertEqual('account', self.stage())
        screen = self.engine.handle_text(self.key, 'Itaú')
        self.assertEqual('confirm', self.stage())
        self.assertEqual(HOJE.isoformat(), self.engine.session(self.key).draft['data'])

    def test_parcelada_so_aparece_no_credito(self):
        self.engine.act(self.key, ('start', 'despesa'))
        self.engine.handle_text(self.key, '350')
        self.engine.handle_text(self.key, 'tênis')
        screen = self.engine.act(self.key, ('answer', 'crédito'))
        self.assertEqual('installment_choice', self.stage())
        self.assertIn('parcelada', screen.text)
        self.engine.act(self.key, ('answer', 'não'))
        self.assertEqual('account', self.stage())
        self.assertEqual('crédito', self.engine.session(self.key).draft['forma_pagamento'])

    def test_receita_nao_pergunta_parcelas(self):
        screen = self.engine.act(self.key, ('start', 'receita'))
        self.assertNotIn('parcelada', screen.text)

    def test_dia_explicito_no_texto_e_entendido_sem_perguntar_a_data(self):
        # Com o parser tolerante (Fase 2), "dia 15" vira data real e aparece na prévia.
        self.engine.handle_text(self.key, 'gastei 45 no mercado dia 15 pix Itaú')
        draft = self.engine.session(self.key).draft
        self.assertEqual('2026-09-15', draft.get('data'))
        self.assertFalse(draft.get('_data_ambigua'))
        self.assertEqual('confirm', self.stage())

    def test_contas_ordenadas_por_uso(self):
        self.tx('a', conta='Bradesco', dia='2026-09-01')
        for i in range(3):
            self.tx('b', conta='Nubank', dia='2026-09-0%d' % (i + 2))
        self.tx('c', conta='Itaú', dia='2026-09-06')
        self.tx('c', conta='Itaú', dia='2026-09-07')
        self.assertEqual(['Nubank', 'Itaú', 'Bradesco'], sug.ordenar_contas(['Bradesco', 'Itaú', 'Nubank']))
        self.engine.handle_text(self.key, 'gastei 45 na loja pix')
        screen = self.engine.session(self.key)
        screen = self.engine.prompt(self.engine.session(self.key))
        labels = [label for row in screen.rows for label, a in row if a[0] == 'answer']
        self.assertEqual(['Nubank', 'Itaú', 'Bradesco'], labels)


class RepetirEFrequentes(Base):
    def test_sem_historico_tela_registrar_como_antes(self):
        screen = self.engine.render(self.key, 'register')
        self.assertFalse(self.acoes(screen, 'repeat'))

    def test_botoes_repetir_e_frequentes(self):
        for dia in ('2026-09-01', '2026-09-08', '2026-09-15'):
            self.tx('café', dia=dia, valor=6.5, cat='Alimentação')
        self.tx('uber', dia='2026-09-16', valor=23.5, cat='Transporte', forma='pix', conta='Nubank')
        self.tx('uber', dia='2026-09-17', valor=23.5, cat='Transporte', forma='pix', conta='Nubank')
        self.tx('tv', dia='2026-09-17', valor=900, parcelas=3)
        self.tx('tv', dia='2026-09-17', valor=900, parcelas=3)
        screen = self.engine.render(self.key, 'register')
        textos = [label for row in screen.rows for label, _ in row]
        self.assertTrue(any('Repetir último' in t for t in textos))
        freq = [t for t in textos if t.startswith('⭐')]
        self.assertEqual(2, len(freq))  # parcelados fora
        self.assertIn('café', freq[0])  # mais usado primeiro
        self.assertLessEqual(len(self.acoes(screen, 'repeat')), 1 + 5)

    def test_repetir_abre_rascunho_com_hoje_e_chave_nova_sem_gravar(self):
        tid = self.tx('café', dia='2026-09-01', valor=6.5, cat='Alimentação')
        antes = self.count()
        screen = self.engine.act(self.key, ('repeat', tid))
        self.assertEqual('confirm', self.stage())
        draft = self.engine.session(self.key).draft
        self.assertEqual(HOJE.isoformat(), draft['data'])
        k1 = draft['key']
        self.assertEqual(antes, self.count())
        self.engine.act(self.key, ('cancel',))
        self.engine.act(self.key, ('repeat', tid))
        self.assertNotEqual(k1, self.engine.session(self.key).draft['key'])
        self.assertTrue(self.acoes(screen, 'commit'))

    def test_repetir_credito_pos_corte_pergunta_a_fatura(self):
        engine = ux.Experience(date_provider=lambda: date(2026, 9, 30))
        tid = self.tx('cinema', forma='crédito', conta='Nubank', dia='2026-08-10', cat='Lazer')
        engine.act(self.key, ('repeat', tid))
        self.assertEqual('billing_month', engine.session(self.key).stage)

    def test_repetir_parcelado_recusa(self):
        tid = self.tx('tv', parcelas=3, forma='crédito', conta='Nubank')
        with self.assertRaises(ValueError):
            self.engine.act(self.key, ('repeat', tid))

    def test_modo_ocultar_mascara_valores_dos_atalhos(self):
        for dia in ('2026-09-01', '2026-09-08'):
            self.tx('café', dia=dia, valor=6.5)
        self.engine.session(self.key).privacy = True
        screen = self.engine.render(self.key, 'register')
        freq = [label for row in screen.rows for label, _ in row if label.startswith('⭐')]
        self.assertTrue(freq)
        self.assertNotIn('6,50', freq[0])

    def test_callbacks_curtos(self):
        for dia in ('2026-09-01', '2026-09-08'):
            self.tx('café', dia=dia)
        screen = self.engine.render(self.key, 'register')
        for row in screen.rows:
            for _, a in row:
                self.assertLessEqual(len(repr(a).encode()), 64)


if __name__ == '__main__':
    unittest.main()
