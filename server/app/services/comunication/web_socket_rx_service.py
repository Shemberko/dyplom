import rx
from rx.subject import Subject
from rx import operators as ops

class WebSocketRxService:
    def __init__(self, broker):
        self.broker = broker
        self.subject = Subject()
        self._setup_rx()

    def _setup_rx(self):
        # Stream for messages with give_info == True
        self.subject.pipe(
            ops.filter(lambda msg: isinstance(msg, dict) and msg.get("give_info") is True)
        ).subscribe(
            lambda msg: print("Give Info Message:", msg)
        )

        # Stream for all other messages, batch by 10
        # Stream: Uppercase, filter "CLICK", take 10, skip 2, debounce, buffer by 3, flatten, reduce
        self.subject.pipe(
            ops.map(lambda msg: msg.upper() if isinstance(msg, str) else msg),
            ops.skip(2),
            ops.take(10),
            ops.debounce(0.1),
            ops.buffer_with_count(3),
            ops.flat_map(lambda msgs: rx.from_(msgs)),
            ops.reduce(lambda acc, msg: f"{acc}|{msg}")
        ).subscribe(
            lambda result: print("Reduced message string:", result)
        )

        # Original batch by 10 for other messages
        self.subject.pipe(
            ops.filter(lambda msg: not (isinstance(msg, dict) and msg.get("give_info") is True)),
            ops.buffer_with_count(10)
        ).subscribe(
            lambda batch: print("Batch of 10 messages:", batch)
        )

    async def handle(self):
        await self.broker.connect()
        while True:
            data = await self.broker.receive()
            self.subject.on_next(data)
            
            # await self.broker.send(f"Echo: {data}")