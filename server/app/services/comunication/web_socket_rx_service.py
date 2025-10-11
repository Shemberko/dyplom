import json

# import asyncio
# from rx.subject import Subject
# from rx import operators as ops

# class WebSocketRxService:
#     def __init__(self, broker, give_info_handler=None, reduced_message_handler=None):
#         self.broker = broker
#         self.give_info_handler = give_info_handler
#         self.reduced_message_handler = reduced_message_handler
#         self.subject = Subject()
#         self._setup_rx()
    
#     def _setup_rx(self):
#         # Handler for "give_info" messages
#         self.subject.pipe(
#             ops.filter(lambda msg: isinstance(msg, dict) and msg.get("give_info") is True)
#         ).subscribe(
#             self.give_info_handler if self.give_info_handler else lambda msg: print("Give Info Message:", msg)
#         )

#         def sync_handler(result):
#             try:
#                 loop = asyncio.get_running_loop()
#             except RuntimeError:
#                 loop = asyncio.get_event_loop_policy().get_event_loop()
#             if self.reduced_message_handler:
#                 loop.call_soon_threadsafe(
#                     lambda: asyncio.create_task(self.reduced_message_handler(result))
#                 )
#             else:
#                 print("||Reduced message string:", result)

#         # Handler for reduced message string
#         self.subject.pipe(
#             ops.debounce(0.1),
#             ops.buffer_with_count(3),
#         ).subscribe(
#             sync_handler
#         )

#     async def handle(self):
#         await self.broker.connect()
#         while True:
#             data = await self.broker.receive()
#             self.subject.on_next(data)

class WebSocketRxService:
    def __init__(self, broker, send_broker, batch_size=3):
        self.broker = broker
        self.send_broker = send_broker
        self.batch_size = batch_size
        self.buffer = []

    async def handle(self):
        await self.broker.connect()
        while True:
            data = await self.broker.receive()
            self.buffer.append(data)
            if len(self.buffer) >= self.batch_size:
                await self.send_batch()

    async def send_batch(self):
        # Відправити список повідомлень як JSON
        print("Sending batch:", self.buffer)
        batch = json.dumps(self.buffer)
        await self.send_broker.send(batch)
        self.buffer.clear()
