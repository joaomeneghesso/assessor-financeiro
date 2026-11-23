"""Ponte assíncrona para o motor financeiro síncrono.

Um único worker preserva a ordem de leituras e gravações. O loop do Telegram
permanece livre para ACKs, indicadores, alertas e operações de rede.
"""
import asyncio
import contextvars
from concurrent.futures import ThreadPoolExecutor
from functools import partial


_CORE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="assessor-core")


async def executar_core(funcao, *args, **kwargs):
    loop = asyncio.get_running_loop()
    contexto = contextvars.copy_context()
    chamada = partial(contexto.run, funcao, *args, **kwargs)
    return await loop.run_in_executor(_CORE_EXECUTOR, chamada)
