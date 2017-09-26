'''
'''
class Packet:
    fields = []

    @property
    def encoded(self):
        return self.json

    def dict(self):
        return

    @property
    def json(self):
        return json.dumps({}).encode('utf-8')

    @classmethod
    def from_json(cls, json_):
        pass

class Heartbeat(Packet):
    pass

class Request(Packet):
    pass

class Response(Packet):
    pass
