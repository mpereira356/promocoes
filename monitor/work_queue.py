"""Uma tarefa por vez; entradas continuam sendo recebidas e enfileiradas."""
import asyncio
from collections import deque


class WorkQueue:
    def __init__(self):
        self.items = deque()
        self.ready = asyncio.Event()
        self.worker = None
        self.active = False
        self.closed = False
        self.child_count = 0

    @property
    def busy(self):
        return self.active or bool(self.items)

    def start(self):
        if self.worker is None:
            self.worker = asyncio.create_task(self._work())

    def submit(self, factory, *, cleanup=None, owner=None):
        if self.closed:
            if cleanup:
                cleanup()
            raise RuntimeError('queue_closed')
        future = asyncio.get_running_loop().create_future()
        future.owner = owner
        # Consumir excecoes mesmo quando o chamador apenas agenda uma tarefa.
        future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        job = (factory, future, cleanup)
        # Trabalho iniciado por um comando pertence a esse pedido e termina
        # antes do proximo comando, inclusive o envio dos resultados.
        if asyncio.current_task() is self.worker:
            self.items.insert(self.child_count, job)
            self.child_count += 1
        else:
            self.items.append(job)
        self.ready.set()
        self.start()
        return future

    def cancel_pending(self, owner):
        retained = deque()
        count = 0
        for job in self.items:
            _, future, cleanup = job
            if future.owner == owner:
                if cleanup:
                    cleanup()
                future.cancel()
                count += 1
            else:
                retained.append(job)
        self.items = retained
        return count

    async def run(self, factory):
        if asyncio.current_task() is self.worker:
            return await factory()
        return await asyncio.shield(self.submit(factory))

    async def _work(self):
        while True:
            await self.ready.wait()
            while self.items:
                factory, future, cleanup = self.items.popleft()
                self.active = True
                self.child_count = 0
                try:
                    result = await factory()
                    if not future.done():
                        future.set_result(result)
                except asyncio.CancelledError:
                    future.cancel()
                    raise
                except Exception as exc:
                    if not future.done():
                        future.set_exception(exc)
                finally:
                    self.active = False
            self.ready.clear()

    async def close(self):
        self.closed = True
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
        while self.items:
            _, future, cleanup = self.items.popleft()
            if cleanup:
                cleanup()
            future.cancel()


class _DeferredCallback:
    def __init__(self, original):
        self.original = original

    def __getattr__(self, name):
        return getattr(self.original, name)

    async def answer(self, text=None, show_alert=False, **kwargs):
        # O callback foi reconhecido ao entrar na fila. Seu ID pode ter
        # expirado quando chegar a vez; detalhes posteriores vao por mensagem.
        if text:
            await self.original.message.reply_text(text)


class _DeferredUpdate:
    def __init__(self, original):
        self.original = original
        self.callback_query = _DeferredCallback(original.callback_query)

    def __getattr__(self, name):
        return getattr(self.original, name)


def queued_handler(queue, callback, config):
    async def handle(update, context):
        from .selection import authorized
        from .telegram_text import send_text
        if not authorized(update, config):
            return await callback(update, context)
        owner = (update.effective_chat.id, update.effective_user.id)
        text = update.effective_message.text or ''
        command = text.split(maxsplit=1)[0].split('@')[0].lower() if text else ''
        if not update.callback_query and command == '/cancelar':
            cancelled = queue.cancel_pending(owner)
            await send_text(update.effective_message.reply_text,
                            f'Cancelamento recebido. Pedidos retirados da fila: {cancelled}. '
                            'Uma consulta já em execução poderá terminar.')
            return await callback(update, context)
        waiting = queue.busy
        gate = asyncio.Event()
        deferred = _DeferredUpdate(update) if waiting and update.callback_query else update

        async def execute():
            await gate.wait()
            try:
                await callback(deferred, context)
            except asyncio.CancelledError:
                raise
            except Exception:
                await send_text(update.effective_message.reply_text,
                                '⚠️ Não foi possível concluir este pedido. A fila continuará com o próximo.')

        queue.submit(execute, owner=owner)
        try:
            if waiting:
                if update.callback_query:
                    try:
                        await update.callback_query.answer('Pedido colocado na fila.')
                    except Exception:
                        pass
                await send_text(update.effective_message.reply_text,
                                '⏳ Seu pedido entrou na fila\nAvisarei quando chegar a sua vez.')
        except Exception:
            pass  # Falha no aviso nao descarta o pedido nem trava a fila.
        finally:
            gate.set()
    return handle
