class Connection(object):

    def __init__(self, name: str, requestType: str, URL: str, content: str = "", headers: dict[str:str] = ""):
        self.name: str = name
        self.requestType: str = requestType
        self.URL: str = URL
        self.content: str = content
        self.headers: dict[str:str] = headers

    def __str__(self):
        return f"{self.name}{self.requestType}"
