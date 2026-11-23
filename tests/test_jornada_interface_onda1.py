"""Onda 1 — defeitos de jornada na interface (docs/reavaliacao/04_jornadas.md).

Banco temporário e data fixa; nada toca data/financeiro.db.
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

HOJE = date(2026, 11, 9)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.t = [1000.0]
        self.engine = ux.Experience(date_provider=lambda: HOJE, clock=lambda: self.t[0])
        p = patch.object(ux, 'EXPERIENCE', self.engine)
        p.start()
        self.addCleanup(p.stop)
        self.sent = []

        async def fake_send(update, screen, host, edit=False):
            self.sent.append(screen)
        p = patch.object(ux, 'send_screen', fake_send)
        p.start()
        self.addCleanup(p.stop)
        self.key = '1:1'
        self.host = SimpleNamespace(
            PENDENCIAS_GUIADAS={}, PENDENCIAS_EXCLUSAO={}, obter_chat_id_update=lambda u: 1,
            limpar_pendencia_guiada=Mock(), limpar_pendencia_exclusao=Mock(), marcar_acesso_seguro=Mock(),
            registrar_mensagem_enviada=Mock(), bloquear_se_assessor_travado=AsyncMock(return_value=False),
            enviar_acao_digitando=AsyncMock(), enviar_acao_enviando_foto=AsyncMock(),
            enviar_resposta=AsyncMock(), iniciar_fluxo_guiado=AsyncMock(), bloquear_assessor=Mock(),
            topics_command=AsyncMock())

    def dispatch(self, texto):
        """Caminho real do Telegram: dispatch_text; False = o app.py mandaria ao legado."""
        self.sent.clear()
        chat = SimpleNamespace(id=1, send_message=AsyncMock(), send_photo=AsyncMock())
        update = SimpleNamespace(message=SimpleNamespace(text=texto, reply_text=AsyncMock()), callback_query=None,
                                 effective_user=SimpleNamespace(id=1), effective_chat=chat,
                                 effective_message=SimpleNamespace(message_thread_id=None))
        return asyncio.run(ux.dispatch_text(update, SimpleNamespace(), self.host))

    def tx(self, desc='mercado', forma='débito', conta='Itaú', dia='2026-11-05', valor=40, cat='Mercado',
           tipo='despesa', parcelas=1):
        return db.inserir_transacao(dict(data=dia, tipo=tipo, valor=valor, categoria=cat, descricao=desc,
                                         conta=conta, forma_pagamento=forma, parcelas_total=parcelas))

    def linhas(self, sql='SELECT id, tipo, valor, data FROM transacoes'):
        with db.get_connection() as c:
            return [tuple(r) for r in c.execute(sql).fetchall()]

    @staticmethod
    def acoes(screen, kind=None):
        return [tuple(a) for row in screen.rows for _, a in row if a and (kind is None or a[0] == kind)]


class EntradaPrevistaNaoViraDespesa(Base):
    """D01: "nova entrada prevista freela 800 dia 20" gravava DESPESA em 20/10 sem prévia."""

    def test_parser_recusa_entrada_sem_data_completa(self):
        r = svc.parsear_comando_entrada_avulsa('nova entrada prevista freela 800 dia 20')
        self.assertEqual('data', r.get('erro'))
        self.assertIn('Nada foi registrado', r['exemplo'])
        self.assertEqual('data', svc.parsear_comando_entrada_avulsa('entrada freela 800')['erro'])
        # Data completa continua aceita; "receita federal 300" continua livre.
        self.assertEqual('2026-11-20', svc.parsear_comando_entrada_avulsa('entrada freela 800 em 2026-11-20')['data'])
        self.assertIsNone(svc.parsear_comando_entrada_avulsa('receita federal 300'))
        self.assertIsNone(svc.parsear_comando_entrada_avulsa('nova entrada fixa salário 3800 dia 5'))

    def test_legado_nunca_grava_despesa(self):
        resposta = svc.processar_mensagem('nova entrada prevista freela 800 dia 20', sessao=self.key)
        self.assertEqual([], self.linhas())
        self.assertNotIn('Despesa registrada', resposta)
        self.assertIn('Nada foi registrado', resposta)

    def test_telegram_responde_nativo_sem_gravar(self):
        self.assertTrue(self.dispatch('nova entrada prevista freela 800 dia 20'))
        self.assertEqual([], self.linhas())
        tela = self.sent[-1]
        self.assertIn('Nada foi registrado', tela.text)
        self.assertIn(('start', 'receita'), self.acoes(tela))


class OcultarPersiste(Base):
    """D04: Ocultar desligava sozinho após "cancelar", "confirmar" ou 10 min parado."""

    def ligar(self):
        self.engine.act(self.key, ('view', 'home'))
        self.engine.act(self.key, ('privacy',))
        self.assertTrue(self.engine.session(self.key).privacy)

    def test_sobrevive_a_cancelar_digitado(self):
        self.ligar()
        self.dispatch('cancelar')
        tela = self.engine.act(self.key, ('view', 'home'))
        self.assertTrue(self.engine.session(self.key).privacy)
        self.assertNotRegex(tela.text, r'R\$\s*\d')

    def test_sobrevive_a_confirmar_digitado(self):
        self.ligar()
        self.dispatch('confirmar')
        self.assertTrue(self.engine.session(self.key).privacy)

    def test_sobrevive_a_expiracao_da_sessao(self):
        self.ligar()
        self.t[0] += ux.TTL + 1
        tela = self.engine.act(self.key, ('view', 'home'))
        self.assertTrue(self.engine.session(self.key).privacy)
        self.assertNotRegex(tela.text, r'R\$\s*\d')

    def test_sobrevive_a_novo_motor(self):
        self.ligar()
        outro = ux.Experience(date_provider=lambda: HOJE)
        self.assertTrue(outro.session(self.key).privacy)

    def test_desligar_tambem_persiste(self):
        self.ligar()
        self.engine.act(self.key, ('privacy',))
        self.t[0] += ux.TTL + 1
        self.assertFalse(self.engine.session(self.key).privacy)


class OutrosAjustesNaoAbreRegistro(Base):
    """D07: "Outros ajustes" mandava "lançamento N" ao handle_text, que lia R$ N."""

    def test_botao_vai_direto_ao_legado(self):
        tid = self.tx()
        tela = self.engine.act(self.key, ('transaction', tid))
        outros = [a for row in tela.rows for lab, a in row if 'Outros ajustes' in lab]
        self.assertEqual([('legacy_raw', f'lançamento {tid}')], outros)
        # dispatch_callback com 'legacy_raw' não passa por handle_text.
        self.engine.session(self.key).tokens['ux:outros'] = outros[0]
        q = SimpleNamespace(data='ux:outros', message=SimpleNamespace(text='', caption=None, reply_text=AsyncMock()),
                            answer=AsyncMock(), edit_message_text=AsyncMock())
        upd = SimpleNamespace(callback_query=q, message=None, effective_user=SimpleNamespace(id=1),
                              effective_chat=SimpleNamespace(id=1, send_message=AsyncMock()),
                              effective_message=SimpleNamespace(message_thread_id=None))
        with patch.object(self.engine, 'handle_text', side_effect=AssertionError('não deveria interpretar')):
            asyncio.run(ux.dispatch_callback(upd, SimpleNamespace(), self.host))
        self.host.enviar_resposta.assert_awaited()
        self.assertIsNone(self.engine.session(self.key).draft)
        self.assertEqual(1, len(self.linhas()))


class CorrigirDataPeloDetalhe(Base):
    """Lacuna: não havia como corrigir a DATA de um lançamento."""

    def test_prevista_confirmacao_e_auditoria(self):
        tid = self.tx(dia='2026-11-05')
        tela = self.engine.act(self.key, ('transaction', tid))
        self.assertIn(('date_menu', tid), self.acoes(tela))
        menu = self.engine.act(self.key, ('date_menu', tid))
        ontem = [a for a in self.acoes(menu, 'date_preview') if a[2] == '2026-11-08'][0]
        previa = self.engine.act(self.key, ontem)
        self.assertIn('05/11/2026', previa.text)
        self.assertIn('08/11/2026', previa.text)
        self.assertEqual('2026-11-05', self.linhas()[0][3])  # prévia não grava
        confirmar = self.acoes(previa, 'date_confirm')[0]
        feito = self.engine.act(self.key, confirmar)
        self.assertIn('Data atualizada', feito.text)
        self.assertEqual('2026-11-08', self.linhas()[0][3])
        again = self.engine.act(self.key, confirmar)
        self.assertIn('já havia sido confirmada', again.text)
        with db.get_connection() as c:
            n = c.execute("SELECT count(*) FROM auditoria_eventos WHERE entidade='telegram_data'").fetchone()[0]
        self.assertEqual(1, n)

    def test_data_digitada(self):
        tid = self.tx(dia='2026-11-05')
        self.engine.act(self.key, ('date_type', tid))
        self.assertTrue(self.dispatch('03/11/2026'))
        previa = self.sent[-1]
        self.assertTrue(self.acoes(previa, 'date_confirm'))
        self.assertEqual('2026-11-05', self.linhas()[0][3])

    def test_recusa_credito_parcelado_e_futuro(self):
        credito = self.tx(forma='crédito', conta='Nubank')
        tela = self.engine.act(self.key, ('date_menu', credito))
        self.assertIn('crédito', tela.text)
        self.assertFalse(self.acoes(tela, 'date_preview'))
        comum = self.tx()
        futuro = self.engine.act(self.key, ('date_preview', comum, '2026-11-20'))
        self.assertFalse(self.acoes(futuro, 'date_confirm'))
        self.assertEqual('2026-11-05', self.linhas(f'SELECT data FROM transacoes WHERE id={comum}')[0][0])


class AvisoDeLimiteAoSalvar(Base):
    """D11: estourar um limite pelo fluxo novo mostrava só "Registro salvo"."""

    def salvar(self, texto):
        tela = self.engine.handle_text(self.key, texto)
        for _ in range(6):
            commit = self.acoes(tela, 'commit')
            if commit:
                return self.engine.act(self.key, commit[0])
            escolha = (self.acoes(tela, 'answer') or [None])[0]
            self.assertIsNotNone(escolha, tela.text)
            tela = self.engine.act(self.key, escolha)
        self.fail('não chegou ao Salvar')

    def test_aviso_perto_e_estourado(self):
        db.definir_meta('Mercado', 500)
        self.tx(valor=380, dia='2026-11-02')
        perto = self.salvar('gastei 30 no mercado pix itaú')
        self.assertIn('Limite de Mercado perto do fim', perto.text)
        self.assertIn(('view', 'budgets'), self.acoes(perto))
        estourou = self.salvar('gastei 120 no mercado pix itaú')
        self.assertIn('Limite de Mercado estourado', estourou.text)
        self.assertIn('R$ 530,00 de R$ 500,00', estourou.text)

    def test_sem_limite_ou_longe_nao_avisa(self):
        db.definir_meta('Mercado', 5000)
        tela = self.salvar('gastei 30 no mercado pix itaú')
        self.assertNotIn('Limite de', tela.text)

    def test_aviso_respeita_ocultar(self):
        db.definir_meta('Mercado', 100)
        self.engine.act(self.key, ('privacy',))
        tela = self.salvar('gastei 130 no mercado pix itaú')
        self.assertIn('estourado', tela.text)
        self.assertNotRegex(tela.text, r'R\$\s*\d')


class NovoLancamentoNoMeioDoAssistente(Base):
    """Atrito 7: frase de outro lançamento era engolida como resposta da etapa."""

    def test_pergunta_continuar_ou_comecar(self):
        self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.assertEqual('method', self.engine.session(self.key).stage)
        self.assertTrue(self.dispatch('gastei 15 no café pix itaú'))
        tela = self.sent[-1]
        self.assertIn('continuar o registro atual ou começar este', tela.text)
        self.assertEqual(45, float(self.engine.session(self.key).draft['valor']))  # atual intacto
        self.assertEqual([], self.linhas())
        continuar = self.engine.act(self.key, self.acoes(tela, 'conflict_keep')[0])
        self.assertIn('Como foi pago', continuar.text)
        novo = self.engine.act(self.key, self.acoes(tela, 'conflict_start')[0])
        self.assertEqual(15, float(self.engine.session(self.key).draft['valor']))
        self.assertTrue(self.acoes(novo, 'commit') or self.acoes(novo, 'answer'))
        self.assertEqual([], self.linhas())

    def test_descricao_comum_continua_resposta(self):
        self.engine.handle_text(self.key, 'gastei 45')
        stage = self.engine.session(self.key).stage
        self.dispatch('Trocar óleo do carro')
        self.assertFalse(any('começar este' in t.text for t in self.sent))
        self.assertNotEqual(stage, None)


class SessaoExpirada(Base):
    """Atrito 10: resposta depois de expirar caía no legado com erro sem relação."""

    def test_resposta_solta_depois_de_expirar(self):
        self.engine.handle_text(self.key, 'gastei 45 no mercado')
        self.t[0] += ux.TTL + 5
        self.assertTrue(self.dispatch('pix'))
        tela = self.sent[-1]
        self.assertIn('expirou', tela.text)
        self.assertIn(('view', 'register'), self.acoes(tela))
        self.assertEqual([], self.linhas())
        # A próxima mensagem já segue normal (sessão nova).
        self.assertFalse(self.engine.session(self.key).stage)

    def test_confirmar_depois_de_expirar(self):
        self.engine.handle_text(self.key, 'gastei 45 no mercado pix itaú')
        self.t[0] += ux.TTL + 5
        self.assertTrue(self.dispatch('confirmar'))
        self.assertIn('expirou', self.sent[-1].text)
        self.assertEqual([], self.linhas())


class LimiteCategoriaPorBotoes(Base):
    def test_categoria_por_botao(self):
        tela = self.engine.act(self.key, ('budget_start',))
        cats = self.acoes(tela, 'budget_cat')
        self.assertTrue(cats)
        mercado = [a for a in cats if a[1] == 'Mercado'][0]
        self.engine.act(self.key, mercado)
        self.assertEqual('budget_amount', self.engine.session(self.key).stage)
        conf = self.engine.handle_text(self.key, '600')
        self.assertIn('Mercado', conf.text)
        self.assertEqual([], [dict(m) for m in db.listar_metas()])  # só grava ao confirmar


class NovoFixoMesPorTexto(Base):
    def test_inicio_aceita_mes_por_nome_e_barra(self):
        s = self.engine.session(self.key)
        for texto in ('dezembro', '12/2026'):
            s.new_fixed = {'nome': 'Seguro', 'valor': 80.0}
            s.stage = 'new_fixed_start'
            self.engine.handle_text(self.key, texto)
            self.assertEqual('2026-12', s.new_fixed['data_inicio'])


class FrasesNaturaisComTelaNativa(Base):
    def test_rotas(self):
        self.tx(desc='uber', conta='Itaú')
        self.assertIn('Histórico', self.engine.handle_text(self.key, 'extrato itau').text)
        self.assertEqual('Itaú', self.engine.session(self.key).history_account_filter)
        self.engine.handle_text(self.key, 'buscar uber')
        self.assertEqual('uber', self.engine.session(self.key).search)
        self.assertIn('A pagar', self.engine.handle_text(self.key, 'faturas').text)
        self.assertIn('Gerenciar contas', self.engine.handle_text(self.key, 'minhas contas').text)
        backup = self.engine.handle_text(self.key, 'fazer backup')
        self.assertIn(('legacy_raw', 'backup'), self.acoes(backup))  # PIN segue pelo caminho existente
        self.assertEqual(1, len(self.linhas()))

    def test_filtrar_por_conta_tem_saida(self):
        tela = self.engine.act(self.key, ('accounts_for', 'history'))
        self.assertIn(('view', 'home'), self.acoes(tela))


class RotulosSemCorteNoMeio(Base):
    """D32: "Mensalidade da academi" (corte no meio da palavra, sem "…")."""

    def test_cortar(self):
        self.assertEqual('Mensalidade da…', ux.cortar('Mensalidade da academia', 22))
        self.assertEqual('Netflix', ux.cortar('Netflix', 22))
        self.assertEqual('A B', ux.cortar('A   B', 22))

    def test_historico_usa_rotulo_inteiro(self):
        self.tx(desc='Mensalidade da academia de natação')
        tela = self.engine.act(self.key, ('view', 'history'))
        rotulos = [lab for row in tela.rows for lab, a in row if a and a[0] == 'transaction']
        self.assertTrue(rotulos)
        self.assertTrue(all(lab.endswith('…') or len(lab) < 40 for lab in rotulos), rotulos)
        self.assertFalse(any('natação' in lab or lab.endswith('nat') for lab in rotulos), rotulos)


if __name__ == '__main__':
    unittest.main()
