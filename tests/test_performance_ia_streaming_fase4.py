import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import assessor_ia_local as ia
from telegram_streaming import DraftProgress


class IaLocalFase4Tests(unittest.TestCase):
    def setUp(self):
        ia.reset_runtime_state_for_tests()

    def tearDown(self):
        ia.reset_runtime_state_for_tests()

    def test_modelo_instalado_e_cacheado_por_ttl(self):
        resposta={"models":[{"name":"teste:latest","size":2_000_000,"details":{"format":"gguf"}}]}
        with patch.dict(os.environ,{"ASSESSOR_IA_LOCAL_MODELO":"teste:latest"}),patch.object(ia,"_request",return_value=resposta) as request:
            self.assertEqual("teste:latest",ia.modelo_local())
            self.assertEqual("teste:latest",ia.modelo_local())
        request.assert_called_once_with('/api/tags')

    def test_circuit_breaker_interrompe_retentativas_repetidas(self):
        connection=SimpleNamespace(connect=lambda:(_ for _ in ()).throw(OSError("offline")),close=lambda:None)
        with patch.dict(os.environ,{"ASSESSOR_IA_CIRCUIT_FAILURES":"2","ASSESSOR_IA_CIRCUIT_SECONDS":"30"}),patch.object(ia.http.client,"HTTPConnection",return_value=connection) as factory:
            with self.assertRaises(ia.LocalUnavailable):ia._request('/api/tags')
            with self.assertRaises(ia.LocalUnavailable):ia._request('/api/tags')
            with self.assertRaises(ia.LocalUnavailable):ia._request('/api/tags')
        self.assertEqual(2,factory.call_count)

    def test_conexao_e_resposta_possuem_timeouts_separados(self):
        sock=SimpleNamespace(settimeout=unittest.mock.Mock())
        response=SimpleNamespace(status=200,read=lambda limit:b'{}')
        connection=SimpleNamespace(sock=sock,connect=lambda:None,request=lambda *a,**k:None,
                                   getresponse=lambda:response,close=lambda:None)
        with patch.dict(os.environ,{"ASSESSOR_IA_CONNECT_TIMEOUT":"0.25","ASSESSOR_IA_RESPONSE_TIMEOUT":"3"}),patch.object(ia.http.client,"HTTPConnection",return_value=connection) as factory:
            self.assertEqual({},ia._request('/api/tags'))
        self.assertEqual(.25,factory.call_args.kwargs['timeout'])
        sock.settimeout.assert_called_once_with(3.0)


class StreamingAtrasadoFase4Tests(unittest.IsolatedAsyncioTestCase):
    def update(self,bot):
        return SimpleNamespace(
            get_bot=lambda:bot,
            effective_chat=SimpleNamespace(id=1,type='private'),
            effective_message=SimpleNamespace(message_thread_id=None),
        )

    async def test_operacao_rapida_nao_faz_chamada_de_progresso(self):
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value=True))
        progress=DraftProgress(self.update(bot),delay=.2,min_interval=0)
        self.assertTrue(await progress.show('Processando…'))
        await progress.close()
        bot.do_api_request.assert_not_awaited()

    async def test_operacao_lenta_publica_um_unico_rascunho(self):
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value=True))
        progress=DraftProgress(self.update(bot),delay=.02,min_interval=1)
        await progress.show('Primeira etapa')
        await progress.show('Etapa mais recente')
        await asyncio.sleep(.05)
        await progress.show('Finalizando')
        await progress.close()
        self.assertEqual(1,bot.do_api_request.await_count)
        payload=bot.do_api_request.await_args.kwargs['api_kwargs']
        self.assertEqual('Etapa mais recente',payload['text'])


if __name__ == '__main__':
    unittest.main()
