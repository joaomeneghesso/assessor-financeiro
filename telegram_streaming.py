"""Progresso efêmero para tarefas locais demoradas, sem estado financeiro."""
import asyncio
import os
import config
import secrets
import time


def enabled():
    value=config.ler('ASSESSOR_STREAMING_PROGRESS','1').strip().lower()
    return value in {'1','true','sim','s','yes','on'}


class DraftProgress:
    """Atualiza um único sendMessageDraft; falhas apenas desativam o recurso."""
    def __init__(self,update,delay=None,min_interval=None):
        self.update_obj=update
        self.draft_id=secrets.randbelow(2_147_483_646)+1
        self.active=False
        self.delay=_seconds(delay,'ASSESSOR_STREAMING_DELAY',0.35,0,3)
        self.min_interval=_seconds(min_interval,'ASSESSOR_STREAMING_MIN_INTERVAL',0.75,0,5)
        self._pending_text=None
        self._delay_task=None
        self._last_send=0.0
        self._closed=False

    def _request(self):
        if not enabled() or self._closed:return None
        chat=getattr(self.update_obj,'effective_chat',None)
        getter=getattr(self.update_obj,'get_bot',None)
        if chat is None or not callable(getter):return None
        if getattr(chat,'type','private')!='private':return None
        request=getattr(getter(),'do_api_request',None)
        return (chat,request) if callable(request) else None

    async def _send(self,text):
        target=self._request()
        if target is None:return False
        chat,request=target
        data={'chat_id':chat.id,'draft_id':self.draft_id,'text':str(text)[:160]}
        try:
            from telegram_recursos import thread_id
            topic=thread_id(self.update_obj)
            if topic:data['message_thread_id']=topic
            await request('sendMessageDraft',api_kwargs=data)
        except Exception as exc:
            if exc.__class__.__name__=='CancelledError':raise
            self.active=False
            return False
        self.active=True
        self._last_send=time.monotonic()
        return True

    async def _send_after_delay(self):
        try:
            await asyncio.sleep(self.delay)
            if not self._closed and self._pending_text is not None:
                text=self._pending_text;self._pending_text=None
                await self._send(text)
        except asyncio.CancelledError:
            return

    async def show(self,text):
        if self._request() is None:return False
        # O texto é sempre definido pelo código chamador. Nunca inclua valores,
        # descrições, nomes de conta ou o conteúdo enviado pelo usuário.
        self._pending_text=str(text)[:160]
        if not self.active and self.delay>0:
            if self._delay_task is None or self._delay_task.done():
                self._delay_task=asyncio.create_task(self._send_after_delay())
            return True
        if self.active and time.monotonic()-self._last_send<self.min_interval:
            return True
        text=self._pending_text;self._pending_text=None
        return await self._send(text)

    async def close(self):
        self._closed=True
        task=self._delay_task
        if task is not None and not task.done():
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
        self._pending_text=None

    async def __aenter__(self):
        return self

    async def __aexit__(self,exc_type,exc,tb):
        await self.close()


def _seconds(explicit,name,default,minimum,maximum):
    try:value=float(config.ler(name,str(default))) if explicit is None else float(explicit)
    except (TypeError,ValueError):value=float(default)
    return max(minimum,min(maximum,value))
