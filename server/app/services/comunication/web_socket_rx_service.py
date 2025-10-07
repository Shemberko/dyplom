import json
import rx
from rx.subject import Subject
from rx import operators as ops

class WebSocketRxService:
    def __init__(self, broker):
        self.broker = broker
        self.subject = Subject()
        self._setup_rx()

    def _setup_rx(self):
        self.subject.pipe(
            ops.filter(lambda msg: isinstance(msg, dict) and msg.get("give_info") is True)
        ).subscribe(
            lambda msg: print("Give Info Message:", msg)
        )

        self.subject.pipe(
            ops.map(lambda msg: {'x': json.loads(msg).get('click').get('x'), 'y': json.loads(msg).get('click').get('y')} ),
            ops.skip(2),
            ops.take(10),
            ops.debounce(0.1),
            ops.buffer_with_count(3),
            ops.reduce(lambda acc, msg: f"{acc}|{msg}")
        ).subscribe(
            lambda result: print("Reduced message string:", result)
        )

    async def handle(self):
        await self.broker.connect()
        while True:
            data = await self.broker.receive()
            self.subject.on_next(data)