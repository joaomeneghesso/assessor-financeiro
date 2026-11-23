import tempfile,unittest
from pathlib import Path
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch,Mock,AsyncMock
import database as db,services as svc,telegram_experiencia as ux
from telegram_visuais import painel
from PIL import Image
from saldo_resumo import resumir_saldo

class DashboardRegressao(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for mod in (db,svc):
            p=patch.object(mod,'DB_PATH',Path(self.tmp.name)/'fixture.db');p.start();self.addCleanup(p.stop)
        db.init_db();db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        self.engine=ux.Experience(date_provider=lambda:date(2026,9,30));self.key='1:1'
        p=patch.object(ux,'EXPERIENCE',self.engine);p.start();self.addCleanup(p.stop)
        self.host=SimpleNamespace(PENDENCIAS_GUIADAS={},PENDENCIAS_EXCLUSAO={},obter_chat_id_update=lambda u:1,
            limpar_pendencia_guiada=Mock(),limpar_pendencia_exclusao=Mock(),marcar_acesso_seguro=Mock(),registrar_mensagem_enviada=Mock(),
            bloquear_se_assessor_travado=AsyncMock(return_value=False),enviar_acao_digitando=AsyncMock())
        self.chat=SimpleNamespace(id=1,send_photo=AsyncMock(),send_message=AsyncMock())
    def update(self,text):
        return SimpleNamespace(message=SimpleNamespace(text=text),callback_query=None,effective_user=SimpleNamespace(id=1),effective_chat=self.chat)
    def test_dashboard_em_outubro_selecionado_eh_imagem(self):
        self.engine.session(self.key).month='2026-10'
        screen=self.engine.handle_text(self.key,'Dashboard')
        self.assertIsNotNone(screen.image,'Dashboard foi desviado para Inicio textual')
        self.assertIn('Outubro',screen.image['subtitle'])
        with Image.open(painel(screen.image)) as img:
            self.assertEqual('PNG',img.format);self.assertGreater(img.height,500)
    def test_aliases_e_competencia_explicita(self):
        for command in ('Dashboard','dash','painel','📈 Dashboard','/dashboard','Dashboard 2026-09'):
            with self.subTest(command=command):
                self.assertIsNotNone(self.engine.handle_text(self.key,command).image)
        self.engine.session(self.key).month='2026-10'
        screen=self.engine.handle_text(self.key,'Dashboard 2026-09')
        self.assertIn('Setembro',screen.image['subtitle'])
    def test_categorias_nao_cai_no_inicio(self):
        for command in ('dashboard categorias','dash categoria','painel por categorias','categorias dashboard','🏷 Dashboard categorias'):
            with self.subTest(command=command):
                screen=self.engine.handle_text(self.key,command);self.assertIsNotNone(screen.image)
                self.assertEqual('Onde você gastou',screen.image['title'])
    def test_competencia_invalida_nao_muda_mes(self):
        self.engine.session(self.key).month='2026-10'
        with self.assertRaises(ValueError):self.engine.handle_text(self.key,'dashboard 2026-13')
        self.assertEqual('2026-10',self.engine.session(self.key).month)
    def test_dashboard_como_descricao_continua_resposta_do_formulario(self):
        self.engine.begin(self.key,'receita');self.engine.handle_text(self.key,'25')
        self.engine.handle_text(self.key,'Dashboard')
        self.assertEqual('Dashboard',self.engine.session(self.key).draft['descricao'])
    def test_valores_do_grafico_batem_com_resumo_do_inicio(self):
        db.inserir_transacao(dict(data='2026-09-20',tipo='receita',valor=500,categoria='Salário',descricao='Salário',conta='Itaú',forma_pagamento='pix',parcelas_total=1))
        summary=resumir_saldo(svc.obter_metricas_resultado_mes('2026-09'))
        image=self.engine.handle_text(self.key,'Dashboard').image
        fields={c['label']:c['value'] for c in image['cards']+[image['hero']]}
        for label,key in [('SALDO AGORA','saldo_atual'),('RESERVADO PARA PAGAR','reservas_liquidas'),('SOBRA PREVISTA','saldo_final')]:
            self.assertEqual(ux.money(summary[key]),fields[label])
    def test_privacidade_oculta_todos_os_valores_do_grafico(self):
        self.engine.session(self.key).privacy=True
        image=self.engine.handle_text(self.key,'Dashboard').image
        self.assertTrue(all(c['value']=='••••' for c in image['cards']))
        self.assertEqual([],image['bars']);self.assertEqual([],image['details'])
    async def test_dispatcher_entrega_foto_sem_api_real_e_sem_gravacao(self):
        with db.get_connection() as c:before=c.execute('SELECT count(*) FROM transacoes').fetchone()[0]
        self.engine.session(self.key).month='2026-10'
        result=await ux.dispatch_text(self.update('Dashboard'),SimpleNamespace(),self.host)
        self.assertTrue(result);self.chat.send_photo.assert_awaited_once();self.chat.send_message.assert_not_awaited()
        kwargs=self.chat.send_photo.await_args.kwargs
        self.assertIsNotNone(kwargs['reply_markup']);self.assertIn('Outubro',kwargs['caption'])
        with db.get_connection() as c:self.assertEqual(before,c.execute('SELECT count(*) FROM transacoes').fetchone()[0])
    async def test_categoria_no_dispatcher_tambem_entrega_foto(self):
        await ux.dispatch_text(self.update('dashboard categorias 2026-09'),SimpleNamespace(),self.host)
        self.chat.send_photo.assert_awaited_once()
    async def test_foto_abre_detalhes_em_texto_e_invalida_controles_antigos(self):
        screen=self.engine.act(self.key,('chart','home'))
        message=SimpleNamespace(photo=[object()]);query=SimpleNamespace(message=message,edit_message_reply_markup=AsyncMock())
        update=self.update('');update.callback_query=query
        await ux.send_screen(update,self.engine.render(self.key,'home'),self.host,edit=True)
        self.chat.send_message.assert_awaited_once();query.edit_message_reply_markup.assert_awaited_once()
