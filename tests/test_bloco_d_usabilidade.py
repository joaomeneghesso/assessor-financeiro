"""Bloco D: usabilidade do Telegram (rascunhos, tópicos, alertas e relógios).

Cada item tem um teste que reproduz o defeito e testes de preservação do
comportamento normal.
"""
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import app
import conciliacao as conc
import database as db
import security
import services as svc
import telegram_experiencia as ux


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        db.definir_saldo_inicial_conta_mes('2026-09', 'Itaú', 1000)
        self.engine = ux.Experience(date_provider=lambda: date(2026, 9, 30))
        self.key = '1:1'

    def s(self, key=None):
        return self.engine.session(key or self.key)

    def actions(self, screen, kind):
        return [tuple(a) for row in screen.rows for _, a in row if a and a[0] == kind]

    def action(self, screen, kind):
        found = self.actions(screen, kind)
        self.assertTrue(found, f'Botão {kind} ausente: {screen.text}')
        return found[0]

    def counts(self):
        with db.get_connection() as c:
            return tuple(c.execute('SELECT count(*) FROM ' + t).fetchone()[0]
                         for t in ('transacoes', 'compromissos', 'fatura_movimentos'))


class D1RespostasNaoSaoComandos(_Base, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        p = patch.object(ux, 'EXPERIENCE', self.engine)
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

    def update(self, text):
        return SimpleNamespace(message=SimpleNamespace(text=text), callback_query=None,
                               effective_user=SimpleNamespace(id=1), effective_chat=self.chat)

    async def send(self, text):
        return await ux.dispatch_text(self.update(text), SimpleNamespace(), self.host)

    async def test_descricao_iniciada_por_trocar_preserva_o_rascunho(self):
        self.assertTrue(await self.send('gastei 180 pix Itaú'))
        self.assertEqual('description', self.s().stage)
        self.assertTrue(await self.send('Trocar óleo do carro'))
        draft = self.s().draft
        self.assertIsNotNone(draft)
        self.assertEqual('Trocar óleo do carro', draft['descricao'])
        self.assertEqual(180.0, draft['valor'])

    async def test_confirmar_digitado_reexibe_previa_sem_gravar(self):
        before = self.counts()
        await self.send('gastei 42 farmacia pix Itaú')
        self.assertEqual('confirm', self.s().stage)
        draft_key = self.s().draft['key']
        self.assertTrue(await self.send('confirmar'))
        self.assertEqual(before, self.counts())
        self.assertEqual('confirm', self.s().stage)
        self.assertEqual(draft_key, self.s().draft['key'])
        commit = self.action(self.sent[-1], 'commit')
        self.assertEqual(('commit', draft_key), commit)
        self.engine.act(self.key, commit)
        self.assertEqual(before[0] + 1, self.counts()[0])

    async def test_preservacao_cancelar_e_comandos_fora_de_etapa(self):
        await self.send('gastei 180 pix Itaú')
        self.assertFalse(await self.send('cancelar'))
        self.assertNotIn(self.key, self.engine.sessions)
        # Sem etapa ativa, comandos operacionais continuam no fluxo legado.
        self.assertFalse(await self.send('trocar conta do lançamento 3'))
        # Etapas numéricas não estão na lista: o comando continua saindo do fluxo.
        self.engine.act(self.key, ('start', 'expense'))
        self.assertEqual('amount', self.s().stage)
        self.assertFalse(await self.send('ajustar saldo'))
        self.assertNotIn(self.key, self.engine.sessions)


    async def test_cancelar_com_pontuacao_ou_complemento_sai_do_fluxo(self):
        for texto in ('Cancelar.', 'cancelar!', 'cancelar registro'):
            with self.subTest(texto=texto):
                self.engine.invalidate(self.key)
                await self.send('gastei 180 pix Itaú')
                self.assertEqual('description', self.s().stage)
                self.assertFalse(await self.send(texto))
                self.assertNotIn(self.key, self.engine.sessions)

    async def test_comando_digitado_na_previa_mantem_comportamento_anterior(self):
        await self.send('gastei 42 farmacia pix Itaú')
        self.assertEqual('confirm', self.s().stage)
        # Fora "confirmar/salvar", comandos operacionais saem do fluxo como antes.
        self.assertFalse(await self.send('apagar 5'))
        self.assertNotIn(self.key, self.engine.sessions)


class D2RegistroPausadoNaoESobrescrito(_Base):
    def pause_first(self):
        self.engine.handle_text(self.key, 'gastei 75 farmacia pix Itaú')
        self.assertEqual('confirm', self.s().stage)
        self.engine.act(self.key, ('view', 'history'))
        self.assertEqual('farmacia', self.s().suspended_draft['descricao'])

    def test_novo_gasto_por_texto_nao_substitui_pausado(self):
        self.pause_first()
        screen = self.engine.handle_text(self.key, 'gastei 30 uber pix Itaú')
        self.assertIn('pausado', screen.text)
        self.assertIsNone(self.s().draft)
        self.action(screen, 'resume_suspended')
        self.engine.act(self.key, ('view', 'pay'))
        self.assertEqual('farmacia', self.s().suspended_draft['descricao'])
        self.engine.act(self.key, ('resume_suspended',))
        self.assertEqual(75.0, self.s().draft['valor'])

    def test_repetir_vincular_e_baixa_tambem_respeitam_pausado(self):
        tx = db.inserir_transacao(dict(data='2026-09-25', tipo='despesa', valor=80, categoria='Casa', descricao='Internet',
                                       conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        fixed = db.inserir_compromisso(dict(tipo='fixo', nome='Luz', categoria='Casa', valor=90, data_inicio='2026-09-01',
                                            dia_vencimento=25, conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))
        self.pause_first()
        for action in (('repeat', tx), ('link_existing', tx), ('settle', fixed, '2026-09')):
            screen = self.engine.act(self.key, action)
            self.assertIn('pausado', screen.text, action)
            self.assertIsNone(self.s().draft, action)
            self.assertEqual('farmacia', self.s().suspended_draft['descricao'])

    def test_preservacao_descartar_libera_novo_registro(self):
        self.pause_first()
        screen = self.engine.handle_text(self.key, 'gastei 30 uber pix Itaú')
        self.engine.act(self.key, self.action(screen, 'discard_suspended'))
        self.assertIsNone(self.s().suspended_draft)
        self.engine.handle_text(self.key, 'gastei 30 uber pix Itaú')
        self.assertEqual('uber', self.s().draft['descricao'])
        self.assertEqual('confirm', self.s().stage)

    def test_preservacao_sem_pausado_fluxos_iguais(self):
        self.engine.handle_text(self.key, 'gastei 30 uber pix Itaú')
        self.assertEqual('confirm', self.s().stage)
        screen = self.engine.act(self.key, ('start', 'expense'))
        self.assertNotIn('pausado', screen.text)


class D3DesvincularEntreTopicos(_Base):
    def link(self, key):
        db.inserir_compromisso(dict(tipo='fixo', nome='Internet', categoria='Casa', valor=80, data_inicio='2026-09-01',
                                    dia_vencimento=25, conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))
        tx = db.inserir_transacao(dict(data='2026-09-25', tipo='despesa', valor=80, categoria='Casa', descricao='Internet',
                                       conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        screen = self.engine.act(key, ('link_existing', tx))
        if not self.actions(screen, 'choose_target'):
            screen = self.engine.act(key, self.action(screen, 'pick_target'))
        screen = self.engine.act(key, self.action(screen, 'choose_target'))
        self.engine.act(key, self.action(screen, 'commit_link'))
        return conc.listar_vinculos()[-1]['chave']

    def test_mesmo_usuario_e_chat_desvincula_de_outro_topico(self):
        chave = self.link('1:1:topic:7')
        self.assertTrue(conc.desvincular(chave, '1:1'))
        self.assertFalse(any(v['chave'] == chave for v in conc.listar_vinculos()))

    def test_preservacao_outro_usuario_ou_chat_continua_recusado(self):
        chave = self.link('1:1:topic:7')
        for intruso in ('2:1', '2:1:topic:7', '1:2', '1:2:topic:7', '', None):
            with self.assertRaises(conc.ConciliacaoError):
                conc.desvincular(chave, intruso)
        self.assertTrue(conc.desvincular(chave, '1:1:topic:7'))
        self.assertFalse(conc._mesmo_titular('1:1', '11:1'))
        self.assertFalse(conc._mesmo_titular('1:1:topic:7', '1:12:topic:7'))


class D4EscolhaDePrevisao(_Base):
    def test_sem_rascunho_gera_valueerror_claro(self):
        with self.assertRaisesRegex(ValueError, 'expirou'):
            self.engine.act(self.key, ('choose_target', 1, '2026-09'))

    def test_escolha_de_outro_rascunho_e_recusada(self):
        db.inserir_compromisso(dict(tipo='fixo', nome='Internet', categoria='Casa', valor=80, data_inicio='2026-09-01',
                                    dia_vencimento=25, conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))
        tx = db.inserir_transacao(dict(data='2026-09-25', tipo='despesa', valor=80, categoria='Casa', descricao='Internet',
                                       conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        screen = self.engine.act(self.key, ('link_existing', tx))
        if not self.actions(screen, 'choose_target'):
            screen = self.engine.act(self.key, self.action(screen, 'pick_target'))
        choose = self.action(screen, 'choose_target')
        self.assertEqual(self.s().draft['key'], choose[3])
        with self.assertRaisesRegex(ValueError, 'outro registro'):
            self.engine.act(self.key, choose[:3] + ('outra-chave',))
        # Preservação: o botão correto e o formato antigo (3 campos) funcionam.
        self.assertTrue(self.actions(self.engine.act(self.key, choose), 'commit_link'))
        self.assertTrue(self.actions(self.engine.act(self.key, choose[:3]), 'commit_link'))


class D5AjudaEncerraEtapa(_Base):
    def setUp(self):
        super().setUp()
        self.s().month = '2026-08'  # mês sem saldos por conta: usa saldo inicial livre
    def test_topico_de_ajuda_nao_deixa_etapa_de_saldo_ativa(self):
        self.engine.act(self.key, ('balance_initial',))
        self.assertEqual('initial_balance', self.s().stage)
        for topic in ('saldo', 'grupo_dinheiro', 'analisar'):
            self.engine.act(self.key, ('topic', topic))
        self.assertIsNone(self.s().stage)
        screen = self.engine.handle_text(self.key, 'aprender auditoria')
        self.assertNotIn('Use um valor como 1000,00', screen.text)

    def test_topico_pausa_registro_em_andamento(self):
        self.engine.handle_text(self.key, 'gastei 75 farmacia pix Itaú')
        self.engine.act(self.key, ('topic', 'saldo'))
        self.assertIsNone(self.s().stage)
        self.assertEqual('farmacia', self.s().suspended_draft['descricao'])

    def test_preservacao_saldo_inicial_sem_ajuda(self):
        self.engine.act(self.key, ('balance_initial',))
        screen = self.engine.handle_text(self.key, '1000')
        self.action(screen, 'save_balance')
        self.engine.act(self.key, ('topic', 'saldo'))  # sem etapa: só navega
        self.assertEqual('saldo', self.s().topic)


class D6HorariosDentroDoSilencio(_Base):
    def test_horario_dentro_do_silencio_e_recusado(self):
        self.engine.act(self.key, ('alert_hours',))
        screen = self.engine.handle_text(self.key, '07:30 23:15 23:00 08:00')
        self.assertIn('silêncio', screen.text)
        self.assertFalse(self.actions(screen, 'save_hours'))
        self.assertEqual('alert_hours', self.s().stage)

    def test_domingo_dentro_do_silencio_gera_aviso(self):
        self.engine.act(self.key, ('alert_hours',))
        screen = self.engine.handle_text(self.key, '09:00 22:30 19:30 21:00')
        self.assertIn('domingo', screen.text.lower())
        self.action(screen, 'save_hours')

    def test_botao_de_horario_dentro_do_silencio_e_recusado(self):
        self.engine.act(self.key, ('alert_hours',))
        self.engine.act(self.key, self.action(self.engine.handle_text(self.key, '11:00 20:00 08:30 10:30'), 'save_hours'))
        with self.assertRaisesRegex(ValueError, 'silêncio'):
            self.engine.act(self.key, ('pref', 'hora_manha', '09:00'))
        self.assertEqual('11:00', ux.orient.preferencias(self.key)['hora_manha'])
        self.assertIn('Escolha', self.engine.render(self.key, 'alert_settings').text)

    def test_preservacao_horarios_validos(self):
        self.engine.act(self.key, ('alert_hours',))
        screen = self.engine.handle_text(self.key, '09:00 20:00 23:00 08:00')
        self.assertNotIn('⚠️', screen.text)
        self.engine.act(self.key, self.action(screen, 'save_hours'))
        self.engine.act(self.key, ('pref', 'hora_manha', '10:00'))
        prefs = ux.orient.preferencias(self.key)
        self.assertEqual(('10:00', '20:00'), (prefs['hora_manha'], prefs['hora_noite']))
        self.assertNotIn('Dentro do silêncio', self.engine.render(self.key, 'alert_settings').text)


class D7RelogioMonotonico(unittest.TestCase):
    def setUp(self):
        self.mono = [1000.0]
        p = patch.object(app, '_monotonic', lambda: self.mono[0])
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(app, 'pin_configurado', lambda: True)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(app.SESSOES_SEGURANCA.pop, 'd7', None)

    def test_autolock_conta_inatividade_real_mesmo_com_relogio_atrasado(self):
        app.desbloquear_assessor('d7')
        self.mono[0] += (app.ASSESSOR_AUTOLOCK_MINUTES + 1) * 60
        self.assertFalse(app.assessor_esta_desbloqueado('d7'))

    def test_preservacao_autolock(self):
        app.desbloquear_assessor('d7')
        self.mono[0] += 60
        self.assertTrue(app.assessor_esta_desbloqueado('d7'))
        app.marcar_acesso_seguro('d7')
        self.mono[0] += (app.ASSESSOR_AUTOLOCK_MINUTES - 1) * 60
        self.assertTrue(app.assessor_esta_desbloqueado('d7'))
        app.SESSOES_SEGURANCA['d7']['ultimo_acesso'] = datetime.now() - timedelta(minutes=app.ASSESSOR_AUTOLOCK_MINUTES + 1)
        self.assertFalse(app.assessor_esta_desbloqueado('d7'))
        app.desbloquear_assessor('d7')
        app.bloquear_assessor('d7')
        self.assertFalse(app.assessor_esta_desbloqueado('d7'))

    def test_bloqueio_de_pin_usa_tempo_monotonico(self):
        clock = SimpleNamespace(monotonic=lambda: self.mono[0])
        with patch.object(security, 'time', clock):
            limiter = security.AuthAttemptLimiter(2, 15)
            limiter.register_failure(1, 1)
            self.assertTrue(limiter.register_failure(1, 1)[0])
            self.assertTrue(limiter.status(1, 1)[0])
            self.mono[0] += 20 * 60  # relógio de parede pode ter voltado; o bloqueio expira mesmo assim
            self.assertEqual((False, 0), limiter.status(1, 1))
            limiter.register_failure(1, 1)
            self.assertEqual(1, limiter._states['pin:1:1'].failures)

    def test_preservacao_now_explicito_continua_em_relogio_de_parede(self):
        limiter = security.AuthAttemptLimiter(1, 5)
        start = datetime(2026, 9, 1, 10, 0)
        limiter.register_failure(1, 10, now=start)
        self.assertTrue(limiter.status(1, 10, now=start + timedelta(minutes=4))[0])
        self.assertFalse(limiter.status(1, 10, now=start + timedelta(minutes=6))[0])


class D8SessaoRestauradaContaTempoParado(unittest.TestCase):
    class Mem:
        def __init__(self):
            self.doc = {}

        def load(self, default):
            return dict(self.doc) or default

        def save(self, value):
            self.doc = value
            return True

    def setUp(self):
        self.t = {'mono': 0.0, 'wall': 1_000_000.0}
        self.store = self.Mem()

    def make(self):
        return ux.Experience(clock=lambda: self.t['mono'], wall_clock=lambda: self.t['wall'],
                             state_store=self.store, date_provider=lambda: date(2026, 9, 30))

    def test_reinicio_nao_renova_ttl(self):
        e = self.make()
        s = e.session('k')
        s.draft = {'flow': 'x', 'valor': 10}
        s.stage = 'confirm'
        e.persist()
        self.t['wall'] += ux.TTL - 10
        self.t['mono'] = 0.0
        e2 = self.make()
        restored = e2.sessions['k']
        self.assertEqual('confirm', restored.stage)
        self.t['mono'] += 30
        self.t['wall'] += 30
        self.assertGreater(e2.clock() - restored.touched, ux.TTL)

    def test_preservacao_reinicio_rapido_mantem_rascunho(self):
        e = self.make()
        s = e.session('k')
        s.draft = {'flow': 'x', 'valor': 10}
        s.stage = 'confirm'
        e.persist()
        self.t['wall'] += 5
        e2 = self.make()
        self.assertEqual({'flow': 'x', 'valor': 10}, e2.session('k').draft)


if __name__ == '__main__':
    unittest.main()
