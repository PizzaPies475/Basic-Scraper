class Connection(object):

    def __init__(self, name: str, requestType: str, URL: str, content: str = "", headers: dict = ""):
        self.name = name
        self.requestType = requestType
        self.URL = URL
        self.content = content
        self.headers = headers

    def __str__(self):
        return f"{self.name}{self.requestType}"
