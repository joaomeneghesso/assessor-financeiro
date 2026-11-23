"""Fase 1 / P1: texto sem verbo, "novo fixo ..." e "transferi ..." não gravam direto.

Antes, esses textos saíam de Experience.handle_text (None) e caíam em
services.processar_mensagem, que gravava na hora, sem prévia. Agora abrem o
rascunho/prévia nativo e só gravam pelo botão Salvar. Banco sempre temporário.
"""
import asyncio
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 10, 20)


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = 'teste-legado'

    def counts(self):
        with db.get_connection() as c:
            return tuple(c.execute('SELECT count(*) FROM ' + t).fetchone()[0]
                         for t in ('transacoes', 'compromissos', 'transferencias_caixa'))

    def acoes(self, screen, kind):
        return [tuple(a) for row in screen.rows for _, a in row if a and a[0] == kind]

    def acao(self, screen, kind):
        found = self.acoes(screen, kind)
        self.assertTrue(found, f'Botão {kind} ausente: {screen.text}')
        return found[0]

    def texto(self, text):
        return self.engine.handle_text(self.key, text)

    def ate_salvar(self, screen):
        """Responde as perguntas do fluxo guiado (não, débito, Itaú, data) até o botão Salvar."""
        for _ in range(8):
            if self.acoes(screen, 'commit'):
                return screen
            stage = self.engine.session(self.key).stage
            if stage == 'installment_choice':
                screen = self.engine.act(self.key, ('answer', 'não'))
            elif stage == 'method':
                screen = self.engine.act(self.key, ('answer', 'débito'))
            elif stage == 'account':
                screen = self.texto('Itaú')
            elif stage == 'date':
                screen = self.engine.act(self.key, ('answer', 'hoje'))
            else:
                self.fail(f'Etapa inesperada {stage}: {screen.text}')
        self.fail('Não chegou ao botão Salvar')


class TextoSemVerboTests(_Base):
    def test_frases_sem_verbo_abrem_rascunho_e_nao_gravam(self):
        casos = {
            'mercado 45': (45.0, 'despesa'),
            'uber 23,50 ontem': (23.5, 'despesa'),
            '45 mercado': (45.0, 'despesa'),
            'salário 5000': (5000.0, 'receita'),
            'caixa de som 200': (200.0, 'despesa'),
        }
        for frase, (valor, tipo) in casos.items():
            with self.subTest(frase=frase):
                self.engine.sessions.clear()
                before = self.counts()
                screen = self.texto(frase)
                self.assertIsNotNone(screen)
                self.assertEqual(before, self.counts())
                draft = self.engine.session(self.key).draft
                self.assertIsNotNone(draft, screen.text)
                self.assertEqual(valor, draft['valor'])
                self.assertEqual(tipo, draft['tipo'])
                self.assertEqual(frase, draft['mensagem_original'])
                self.assertTrue(self.engine.session(self.key).stage)

    def test_data_relativa_e_lida_sem_vazar_para_a_descricao(self):
        self.texto('uber 23,50 ontem')
        draft = self.engine.session(self.key).draft
        self.assertEqual('2026-10-19', draft['data'])
        self.assertNotIn('ontem', draft['descricao'].lower())
        self.assertNotIn('23', draft['descricao'])

    def test_salvar_grava_uma_vez_e_repetir_nao_duplica(self):
        before = self.counts()
        screen = self.ate_salvar(self.texto('mercado 45'))
        self.assertEqual(before, self.counts())  # prévia ainda não gravou
        commit = self.acao(screen, 'commit')
        self.engine.act(self.key, commit)
        self.assertEqual(before[0] + 1, self.counts()[0])
        with db.get_connection() as c:
            row = c.execute('SELECT descricao,valor,conta,forma_pagamento FROM transacoes').fetchone()
        self.assertEqual('Itaú', row[2])
        self.assertEqual(45.0, row[1])
        self.assertNotIn('45', row[0])
        try:
            self.engine.act(self.key, commit)
        except ValueError:
            pass
        self.assertEqual(before[0] + 1, self.counts()[0])

    def test_data_futura_e_texto_ambiguo_continuam_sem_gravar(self):
        before = self.counts()
        for frase in ('mercado 45 amanhã', 'mercado 45 e padaria 20', 'só uma frase qualquer'):
            with self.subTest(frase=frase):
                self.engine.sessions.clear()
                self.texto(frase)  # None (cai no legado, que recusa) ou tela de recusa
                self.assertEqual(before, self.counts())

    def test_frase_com_verbo_continua_no_fluxo_guiado(self):
        screen = self.texto('gastei 45 no mercado')
        draft = self.engine.session(self.key).draft
        # P7: sem forma de pagamento a pergunta é a forma; "parcelada?" só no crédito.
        self.assertEqual('method', self.engine.session(self.key).stage)
        self.assertEqual(45.0, draft['valor'])
        self.assertNotIn('parcelada', screen.text)

    def test_comandos_e_consultas_nao_sao_capturados(self):
        for frase in ('apagar 5', 'mudar 7 para Transporte', 'extrato 2026-07',
                      'quanto gastei com mercado em 2026-07', 'categorias 2026-07',
                      'paguei 500 da fatura Itaú usando Nubank', 'novo gasto'):
            with self.subTest(frase=frase):
                self.engine.sessions.clear()
                with patch.object(self.engine, 'parse_draft') as pd:
                    self.engine._fechar_caminho_legado(self.key, frase)
                    pd.assert_not_called()


class NovoFixoTests(_Base):
    def test_novo_fixo_completo_abre_previa_sem_criar_conta_nem_gravar(self):
        before = self.counts()
        screen = self.texto('novo fixo netflix 55 dia 10 crédito nubank')
        self.assertEqual(before, self.counts())
        d = self.engine.session(self.key).new_fixed
        self.assertEqual('Netflix', d['nome'])
        self.assertEqual(55.0, d['valor'])
        self.assertEqual(10, d['dia_vencimento'])
        self.assertEqual('crédito', d['forma_pagamento'])
        self.assertEqual('Nubank', d['conta_pagamento'])
        self.assertTrue(self.acoes(screen, 'new_fixed_commit'))
        self.assertNotIn('Dia 10 Crédito Nubank', self.engine.accounts())

    def test_salvar_cria_um_fixo_e_repetir_nao_duplica(self):
        self.texto('novo fixo netflix 55 dia 10 crédito nubank')
        self.engine.act(self.key, ('new_fixed_commit',))
        self.assertEqual((0, 1, 0), self.counts())
        with db.get_connection() as c:
            row = c.execute('SELECT nome,valor,dia_vencimento,forma_pagamento,conta_pagamento FROM compromissos').fetchone()
        self.assertEqual(('Netflix', 55.0, 10, 'crédito', 'Nubank'), tuple(row))
        with self.assertRaises(ValueError):
            self.engine.act(self.key, ('new_fixed_commit',))
        self.assertEqual((0, 1, 0), self.counts())

    def test_fixo_incompleto_pergunta_o_que_falta_sem_gravar(self):
        screen = self.texto('novo fixo internet')
        self.assertEqual('new_fixed_amount', self.engine.session(self.key).stage)
        self.assertIn('valor', screen.text.lower())
        self.assertEqual((0, 0, 0), self.counts())

    def test_criar_fixo_tambem_nao_grava(self):
        self.texto('criar fixo spotify 21,90 pix itaú dia 5')
        self.assertEqual((0, 0, 0), self.counts())
        self.assertEqual('Spotify', self.engine.session(self.key).new_fixed['nome'])


class TransferenciaTests(_Base):
    def test_transferencia_abre_previa_sem_gravar_e_sem_artigo_no_destino(self):
        screen = self.texto('transferi 100 do itaú para o nubank')
        self.assertEqual((0, 0, 0), self.counts())
        fields = self.engine.session(self.key).media_review['fields']
        self.assertEqual('Itaú', fields['conta_origem'])
        self.assertEqual('Nubank', fields['conta_destino'])
        self.assertEqual(HOJE.isoformat(), fields['data'])
        self.assertTrue(self.acoes(screen, 'media_transfer_commit'))

    def test_salvar_grava_uma_transferencia_e_repetir_nao_duplica(self):
        screen = self.texto('transferi 100 do itaú para o nubank')
        commit = self.acao(screen, 'media_transfer_commit')
        self.engine.act(self.key, commit)
        self.assertEqual((0, 0, 1), self.counts())
        with self.assertRaises(ValueError):
            self.engine.act(self.key, commit)
        self.assertEqual((0, 0, 1), self.counts())

    def test_transferencia_para_a_mesma_conta_nao_grava(self):
        self.texto('transferi 100 do itaú para o itaú')
        self.assertEqual((0, 0, 0), self.counts())


class DispatchTextTests(_Base, unittest.IsolatedAsyncioTestCase):
    """Caminho real do Telegram: dispatch_text deve tratar a frase e NÃO devolver False (legado)."""

    def setUp(self):
        super().setUp()
        for target, value in ((ux, 'EXPERIENCE'),):
            p = patch.object(target, value, self.engine)
            p.start()
            self.addCleanup(p.stop)
        self.sent = []

        async def fake_send(update, screen, host, edit=False):
            self.sent.append(screen)
        p = patch.object(ux, 'send_screen', fake_send)
        p.start()
        self.addCleanup(p.stop)
        self.host = SimpleNamespace(
            PENDENCIAS_GUIADAS={}, PENDENCIAS_EXCLUSAO={}, obter_chat_id_update=lambda u: 1,
            limpar_pendencia_guiada=Mock(), limpar_pendencia_exclusao=Mock(), marcar_acesso_seguro=Mock(),
            registrar_mensagem_enviada=Mock(), bloquear_se_assessor_travado=AsyncMock(return_value=False),
            enviar_acao_digitando=AsyncMock())
        self.chat = SimpleNamespace(id=1, send_photo=AsyncMock(), send_message=AsyncMock())
        self.key = '1:1'

    async def envia(self, text):
        update = SimpleNamespace(message=SimpleNamespace(text=text), callback_query=None,
                                 effective_user=SimpleNamespace(id=1), effective_chat=self.chat)
        return await ux.dispatch_text(update, SimpleNamespace(), self.host)

    async def test_frases_do_relatorio_nao_chegam_ao_legado(self):
        frases = ['mercado 45', 'uber 23,50 ontem', 'novo fixo netflix 55 dia 10 crédito nubank',
                  'transferi 100 do itaú para o nubank']
        for frase in frases:
            with self.subTest(frase=frase):
                self.engine.sessions.clear()
                self.sent.clear()
                with patch.object(svc, 'processar_mensagem', side_effect=AssertionError('legado chamado')):
                    handled = await self.envia(frase)
                self.assertTrue(handled, 'dispatch_text devolveu False: app.py gravaria pelo legado')
                self.assertEqual((0, 0, 0), self.counts())
                self.assertEqual(1, len(self.sent))


if __name__ == '__main__':
    unittest.main()
