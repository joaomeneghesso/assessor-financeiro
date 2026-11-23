import asyncio
import contextvars
import threading
import time
import unittest

from telegram_execucao import executar_core


class ExecucaoAssincronaFase3Tests(unittest.IsolatedAsyncioTestCase):
    async def test_trabalho_lento_nao_bloqueia_event_loop(self):
        iniciou = threading.Event()
        liberar = threading.Event()

        def lento():
            iniciou.set()
            liberar.wait(timeout=2)
            return "ok"

        tarefa = asyncio.create_task(executar_core(lento))
        while not iniciou.is_set():
            await asyncio.sleep(0)

        inicio = time.perf_counter()
        await asyncio.sleep(0.03)
        decorrido = time.perf_counter() - inicio
        liberar.set()

        self.assertEqual("ok", await tarefa)
        self.assertLess(decorrido, 0.15)

    async def test_operacoes_do_motor_permanecem_serializadas(self):
        ordem = []

        def operacao(nome):
            ordem.append("inicio-" + nome)
            time.sleep(0.02)
            ordem.append("fim-" + nome)
            return nome

        resultados = await asyncio.gather(
            executar_core(operacao, "a"),
            executar_core(operacao, "b"),
        )

        self.assertEqual(["a", "b"], resultados)
        self.assertEqual(["inicio-a", "fim-a", "inicio-b", "fim-b"], ordem)

    async def test_contextvars_sao_preservadas_no_worker(self):
        marcador = contextvars.ContextVar("teste_fase3", default="ausente")
        token = marcador.set("presente")
        try:
            self.assertEqual("presente", await executar_core(marcador.get))
        finally:
            marcador.reset(token)

    async def test_excecao_do_motor_e_devolvida_ao_handler(self):
        def falhar():
            raise ValueError("falha controlada")

        with self.assertRaisesRegex(ValueError, "falha controlada"):
            await executar_core(falhar)


if __name__ == "__main__":
    unittest.main()
