from concurrent.futures import ThreadPoolExecutor

class EventStream:
    def __init__(self, name: str):
        self.name = name
        self.subscribers = []
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.source = None  # Add source tracking

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def notify(self, source=None):
        self.source = source
        for callback in self.subscribers:
            self.executor.submit(callback, self)

    def shutdown(self):
        self.executor.shutdown(wait=False)
