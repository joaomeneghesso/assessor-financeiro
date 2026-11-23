"""Avisos proativos (fase 1): contagens sem valores, noite condicional, alerta_valores e domingo honesto.
Banco temporário; nada toca data/financeiro.db."""
import tempfile,unittest
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
import database as db,services as svc,telegram_alertas as al,assessor_orientacao as orient

HOJE=date(2026,10,28)
def item(dias,valor=100.0,nome='Aluguel do Fulano'):
    return {'data':(HOJE+timedelta(days=dias)).isoformat(),'valor':valor,'nome':nome,'chave':'k'+str(dias)}
def snap(overdue=(),soon=(),tx=(),rev=0):
    return {'cutoff':HOJE.isoformat(),'future':False,'month':'2026-10','overdue':list(overdue),'soon':list(soon),
            'transactions':[{'data':d.isoformat()} for d in tx],'metrics':{'revisoes_conciliacao':[1]*rev}}

class Avisos(unittest.TestCase):
    def test_manha_conta_sem_valores_nem_nomes(self):
        s=snap([item(-3,500)],[item(0,120),item(0,80),item(0,30),item(1,70)])
        t=al.montar_aviso('manha',s,{})
        self.assertIn('3 contas vencem hoje',t);self.assertIn('1 está vencida',t);self.assertIn('1 vence amanhã',t)
        self.assertNotIn('R$',t);self.assertNotIn('Fulano',t)
    def test_manha_sem_nada_nao_envia(self):
        self.assertIsNone(al.montar_aviso('manha',snap(),{}))
        self.assertIsNone(al.montar_aviso('manha',snap(),None))
    def test_manha_proximos_dias_e_conciliacao(self):
        t=al.montar_aviso('manha',snap(soon=[item(4)],rev=2),{})
        self.assertIn('nos próximos dias',t);self.assertIn('2 conciliações',t)
    def test_alerta_valores_padrao_desligado_e_ligado_so_com_total(self):
        self.assertFalse(orient.DEFAULTS['alerta_valores'])
        s=snap([item(-3,500.5)],[item(0,120),item(0,80)])
        self.assertNotIn('R$',al.montar_aviso('manha',s,dict(orient.DEFAULTS)))
        t=al.montar_aviso('manha',s,{'alerta_valores':True})
        self.assertIn('R$ 200,00',t);self.assertIn('R$ 500,50',t);self.assertNotIn('Fulano',t)
        self.assertIn('R$ 700,50',al.montar_aviso('noite',s,{'alerta_valores':True}))
        self.assertNotIn('R$',al.montar_aviso('noite',s,{}))
    def test_preferencia_valida_apenas_booleano(self):
        orient.validar_preferencia('alerta_valores',True)
        with self.assertRaises(ValueError):orient.validar_preferencia('alerta_valores','sim')
    def test_noite_so_quando_ha_algo(self):
        self.assertIsNone(al.montar_aviso('noite',snap(),{}))
        self.assertIsNone(al.montar_aviso('noite',snap(soon=[item(5)]),{}))
        self.assertIsNone(al.montar_aviso('noite',snap(soon=[item(1)]),{}))  # D-1 sozinho: já avisado na manhã
        self.assertIn('1 conta ainda em aberto',al.montar_aviso('noite',snap([item(-1)]),{}))
        self.assertIn('2 contas ainda em aberto',al.montar_aviso('noite',snap(soon=[item(0),item(0)]),{}))
        self.assertIn('1 conciliação',al.montar_aviso('noite',snap(rev=1),{}))
    def test_noite_sem_registro_hoje_apenas_para_quem_tem_habito(self):
        tx=[HOJE-timedelta(days=n) for n in (1,2,3)]
        self.assertIn('Nenhum registro hoje',al.montar_aviso('noite',snap(tx=tx),{}))
        self.assertIsNone(al.montar_aviso('noite',snap(tx=tx[:2]),{}))     # só 2 dias: sem hábito
        self.assertIsNone(al.montar_aviso('noite',snap(tx=tx+[HOJE]),{}))  # registrou hoje
    def test_domingo_nao_promete_revisao_inexistente(self):
        t=al.montar_aviso('semana',snap(),{})
        self.assertNotIn('pronta',t);self.assertIn('Fechamento',t);self.assertIn('Atenção',t);self.assertNotIn('R$',t)
        markup=al.controles('1:1','x',snap(),'semana')
        views={al.ALERT_ACTIONS[b.callback_data]['action'][:2] for row in markup.inline_keyboard for b in row}
        self.assertIn(('view','closing'),views);self.assertIn(('view','attention'),views)
    def test_previa_generica_continua_funcionando(self):
        self.assertIn('fechar o dia',al.montar_aviso('noite',{}))

class Janela(unittest.IsolatedAsyncioTestCase):
    def _setup(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        for m in (db,svc):
            p=patch.object(m,'DB_PATH',Path(tmp.name)/'f.db');p.start();self.addCleanup(p.stop)
        db.init_db();tz=timezone(timedelta(hours=-3))
        host=SimpleNamespace(obter_chat_id_alertas=lambda:1,obter_allowed_user_id=lambda:1,ASSESSOR_ALLOWED_CHAT_ID='1',
                             ASSESSOR_LEMBRETE_PAGAMENTOS_ATIVO=True,ASSESSOR_ALERTAS_ATIVOS=True,obter_timezone_alertas=lambda:tz)
        app=SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))
        return tz,host,app
    async def test_janela_respeita_pausa_idempotencia_e_silencio(self):
        tz,host,app=self._setup();now=datetime(2026,10,28,10,0,5,tzinfo=tz)
        full=snap([item(-2)],[item(0)])
        with patch.object(al,'_snapshot_alerta',return_value=full):
            orient.salvar_preferencia('1:1','pausa_ate','2026-10-30')
            self.assertEqual(0,await al.executar_janela(app,host,now))      # pausa
            orient.salvar_preferencia('1:1','pausa_ate','')
            self.assertEqual(1,await al.executar_janela(app,host,now))
            texto=app.bot.send_message.await_args.kwargs['text'];self.assertIn('1 conta vence hoje',texto);self.assertNotIn('R$',texto)
            self.assertEqual(0,await al.executar_janela(app,host,now))      # idempotente (reservar)
            orient.salvar_preferencia('1:1','hora_manha','23:30')
            self.assertEqual(0,await al.executar_janela(app,host,datetime(2026,10,28,23,30,5,tzinfo=tz)))  # silêncio
    async def test_noite_vazia_nao_reserva_nem_envia(self):
        tz,host,app=self._setup()
        with patch.object(al,'_snapshot_alerta',return_value=snap()):
            self.assertEqual(0,await al.executar_janela(app,host,datetime(2026,10,28,22,0,5,tzinfo=tz)))
        app.bot.send_message.assert_not_awaited()
        self.assertIsNotNone(al.reservar('1:1','2026-10-28','noite'))   # nada foi reservado

if __name__=='__main__':unittest.main()
