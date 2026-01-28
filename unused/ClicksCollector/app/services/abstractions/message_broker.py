from abc import ABC, abstractmethod

class MessageBroker(ABC):
    @abstractmethod
    async def connect(self): pass

    @abstractmethod
    async def send(self, message): pass

    @abstractmethod
    async def receive(self): pass

    @abstractmethod
    async def disconnect(self): pass