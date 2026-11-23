import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.error import NetworkError, TimedOut

import operacao_bot
from operacao_bot import (
    MENSAGEM_ERRO_GENERICA,
    InstanciaJaEmExecucao,
    adquirir_trava_instancia,
    criar_tarefa_monitorada,
    criar_tratador_erro,
)

RAIZ = Path(__file__).resolve().parents[1]


class TravaInstanciaTests(unittest.TestCase):
    def test_segunda_aquisicao_recusada_e_liberacao(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "sub" / "bot.lock"
            trava = adquirir_trava_instancia(caminho)
            try:
                with self.assertRaises(InstanciaJaEmExecucao) as ctx:
                    adquirir_trava_instancia(caminho)
                self.assertIn("já está rodando", str(ctx.exception))
                self.assertIn(caminho.read_text().split()[0], str(ctx.exception))
            finally:
                trava.liberar()
            trava.liberar()  # idempotente
            with adquirir_trava_instancia(caminho):
                pass

    def test_recusada_em_subprocesso(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "bot.lock"
            with adquirir_trava_instancia(caminho):
                codigo = (
                    "import sys\nfrom pathlib import Path\n"
                    "from operacao_bot import adquirir_trava_instancia, InstanciaJaEmExecucao\n"
                    "try:\n    adquirir_trava_instancia(Path(sys.argv[1]))\n"
                    "except InstanciaJaEmExecucao:\n    sys.exit(7)\n"
                )
                r = subprocess.run([sys.executable, "-c", codigo, str(caminho)], cwd=RAIZ)
                self.assertEqual(r.returncode, 7)

    def test_arquivo_stale_e_reaproveitado(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "bot.lock"
            caminho.write_text("999999 2020-01-01T00:00:00\n")
            with adquirir_trava_instancia(caminho):
                self.assertNotEqual(caminho.read_text().split()[0], "999999")


class TratadorErroTests(unittest.IsolatedAsyncioTestCase):
    def _update(self, com_chat=True):
        return SimpleNamespace(
            update_id=42,
            effective_chat=SimpleNamespace() if com_chat else None,
            message=SimpleNamespace(text="SEGREDO-DO-USUARIO"),
        )

    async def test_loga_sem_texto_do_usuario_e_avisa(self):
        aviso = AsyncMock()
        tratador = criar_tratador_erro(aviso)
        ctx = SimpleNamespace(error=ValueError("detalhe-interno"))
        with self.assertLogs("assessor.erros", level="ERROR") as cap:
            await tratador(self._update(), ctx)
        saida = "\n".join(cap.output)
        self.assertIn("42", saida)
        self.assertNotIn("SEGREDO-DO-USUARIO", saida)
        aviso.assert_awaited_once()
        enviado = aviso.await_args.args[1]
        self.assertEqual(enviado, MENSAGEM_ERRO_GENERICA)
        self.assertNotIn("detalhe-interno", enviado)

    async def test_rede_so_warning_sem_aviso(self):
        for erro in (NetworkError("x"), TimedOut("y")):
            aviso = AsyncMock()
            tratador = criar_tratador_erro(aviso)
            with self.assertLogs("assessor.erros", level="WARNING"):
                await tratador(self._update(), SimpleNamespace(error=erro))
            aviso.assert_not_awaited()

    async def test_falha_ao_avisar_e_engolida(self):
        aviso = AsyncMock(side_effect=RuntimeError("falhou"))
        tratador = criar_tratador_erro(aviso)
        with self.assertLogs("assessor.erros", level="WARNING"):
            await tratador(self._update(), SimpleNamespace(error=ValueError("a")))

    async def test_sem_chat_nao_avisa(self):
        aviso = AsyncMock()
        tratador = criar_tratador_erro(aviso)
        with self.assertLogs("assessor.erros", level="ERROR"):
            await tratador(self._update(com_chat=False), SimpleNamespace(error=ValueError("a")))
        aviso.assert_not_awaited()

    async def test_aviso_padrao(self):
        chat = SimpleNamespace(send_message=AsyncMock())
        await operacao_bot.aviso_padrao(SimpleNamespace(effective_chat=chat), "oi")
        chat.send_message.assert_awaited_once_with("oi")


class TarefaMonitoradaTests(unittest.IsolatedAsyncioTestCase):
    async def test_excecao_e_logada_e_removida(self):
        registro = set()

        async def falha():
            raise ValueError("boom")

        with self.assertLogs("assessor.rotinas", level="ERROR") as cap:
            t = criar_tarefa_monitorada(falha(), "rotina-x", registro)
            self.assertIn(t, registro)
            self.assertEqual(t.get_name(), "rotina-x")
            await asyncio.gather(t, return_exceptions=True)
            await asyncio.sleep(0)
        self.assertIn("rotina-x", "\n".join(cap.output))
        self.assertNotIn(t, registro)

    async def test_cancelamento_nao_loga(self):
        registro = set()

        async def espera():
            await asyncio.sleep(10)

        t = criar_tarefa_monitorada(espera(), "r", registro)
        await asyncio.sleep(0)
        t.cancel()
        await asyncio.gather(t, return_exceptions=True)
        await asyncio.sleep(0)
        self.assertNotIn(t, registro)


if __name__ == "__main__":
    unittest.main()
