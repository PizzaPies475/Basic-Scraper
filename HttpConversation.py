from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, gaierror
from ssl import SSLWantReadError, create_default_context, SSLEOFError, SSLSocket
from httpUtils import URL, Connection, CookieJar, getUrlName, Request, getLinksFromHTML, parseResponse, isFileUrl
from typing import Union
import os
from time import sleep


class bColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class HttpConversation:

    def __init__(self, port: int = 443, packetRecvTimeOut: int = 2, log: bool = True, sendOptionalHeaders: bool = False,
                 acceptEncoding: str = "utf-8", recvSize: int = 0, logLocation: str = "HTTP-Logs",
                 maxReferrals: int = 10, maxRetries: int = 5, isSecure: bool = True) -> None:
        self.__clientSocket: socket = None
        self.currConnection: Connection = None
        self.port: int = port
        self.connectionList: list[Connection] = []
        self.packetRecvTimeOut: int = packetRecvTimeOut
        self.keepAlive: bool = False
        self.sendOptionalHeaders: bool = sendOptionalHeaders
        self.cookieJar: CookieJar = CookieJar()
        self.acceptEnc: str = acceptEncoding
        self.log: bool = log
        self.connectionList: list[Connection] = []
        self.receiveSize: int = recvSize
        self.totalData: bytes = b""
        self.logLocation: str = logLocation
        self.maxReferrals: int = maxReferrals
        self.currIndex: int = -1
        self.maxRetries: int = maxRetries
        self.isSecure: bool = isSecure

    def converse(self, connection: Union[Connection, str, URL]) -> None:
        self.currIndex += 1
        if isinstance(connection, str):
            connection: URL = URL(connection)
            connection: Connection = Connection(connection, 'GET', getUrlName(connection))
        if isinstance(connection, URL):
            connection: Connection = Connection(connection, 'GET', getUrlName(connection))
        self.currConnection = connection
        self.currConnection.request = Request(connection.requestType, connection.url, connection.isUserAction,
                                              connection.content, self.cookieJar.getCookiesStr(self.currConnection.url),
                                              connection.headers, acceptEnc=self.acceptEnc)
        if self.log:
            self.__logData(self.currConnection.request, f"{self.currIndex}{self.currConnection.name}_request.txt")
        self.connectionList.append(connection)
        print(f"Connecting to {connection.url}")
        retryCounter: int = 0
        while retryCounter < self.maxRetries:
            try:
                data = self.__sendRecv()
                self.currConnection.response = parseResponse(data, self.currConnection.url)
                break
            except ValueError:
                retryCounter += 1
                if retryCounter == self.maxRetries:
                    raise ConnectionError(f"Could not connect to {connection.url}")
        if self.log:
            self.__logData(self.currConnection.response, f"{self.currIndex}{self.currConnection.name}_response.txt")
        self.__printStatusLine()
        if "connection" in self.currConnection.response.headers and \
                self.currConnection.response.headers['connection'].lower() == 'close':
            self.keepAlive = False
        else:
            self.keepAlive = True
        for cookie in self.currConnection.response.cookies:
            self.cookieJar.addRemoveCookie(cookie)
        if "location" in self.currConnection.response.headers:
            if self.maxReferrals > 0:
                self.maxReferrals -= 1
                self.converse(self.currConnection.response.headers["location"])
                self.maxReferrals += 1
            else:
                raise ValueError("Too many redirects.")

    def __changeHostIfNeeded(self) -> None:
        urlHost: str = self.currConnection.url.domain
        lastConnection = self.getLastConnectionUrl()
        if lastConnection is not None:
            lastHost: str = self.getLastConnectionUrl().domain
        else:
            lastHost: str = ""
        if self.__clientSocket is None or urlHost != lastHost or not self.keepAlive:
            if self.__clientSocket is not None and not self.keepAlive:
                self.__clientSocket.close()
            try:
                ip: str = gethostbyname(urlHost)
            except gaierror:
                raise ValueError(f"Could not resolve host: {urlHost}")
            clientSocket: socket = socket(AF_INET, SOCK_STREAM)
            if self.currConnection.url.scheme == "https" or self.isSecure:
                self.__clientSocket: SSLSocket = create_default_context().wrap_socket(clientSocket,
                                                                                      server_hostname=urlHost)
                clientSocket.close()
            else:
                self.__clientSocket = clientSocket
            self.__clientSocket.connect((ip, self.port))
            self.__clientSocket.settimeout(self.packetRecvTimeOut)

    def getLastConnectionUrl(self) -> URL:
        if self.connectionList:
            return self.connectionList[-1].url
        else:
            return None

    def __sendRecv(self) -> bytes:
        self.__changeHostIfNeeded()
        try:
            self.__clientSocket.send(str(self.currConnection.request).encode())
        except Exception as e:  # TODO add specific exception
            raise e
        # startTime: float = timer()
        # receivedHeaders: bool = False
        # isFirstPacket: bool = True

        data = b""
        isHtml: bool = False
        while b"0\r\n\r\n" not in data:
            try:
                if self.receiveSize > 0:
                    data += self.__clientSocket.recv(self.receiveSize)
                else:
                    data += self.__clientSocket.recv()
            except TimeoutError:
                print(f"{bColors.WARNING}Packet receive ended on timeout.{bColors.ENDC}")
                break
            if not isHtml:
                if b"<html" in data:
                    isHtml = True
            if isHtml:
                if b"</html>" in data:
                    break
        self.totalData += data
        if self.log:
            self.__logData(data, f"{self.currIndex}{self.currConnection.name}_response.txt")
        return data

    def __logData(self, data, fileName: str):
        if not os.path.exists(self.logLocation):
            os.mkdir(self.logLocation)
        with open(f"{self.logLocation}/{fileName}", 'w', encoding="ISO-8859-1") as f:
            if type(data) is bytes:
                data = data.decode("ISO-8859-1")
            elif type(data) is not str:
                try:
                    data = str(data)
                except Exception as e:
                    raise e
            f.write(data)

    def __printStatusLine(self) -> None:
        statusLine = f"{self.currConnection.response.statusCode} {self.currConnection.response.statusMessage}"
        match int(self.currConnection.response.statusCode) // 100:
            case 1:
                statusLine = f"{bColors.OKBLUE}{statusLine}"
            case 2:
                statusLine = f"{bColors.OKGREEN}{statusLine}"
            case 3:
                statusLine = f"{bColors.WARNING}{statusLine}"
            case 4:
                statusLine = f"{bColors.FAIL}{statusLine}"
            case 5:
                statusLine = f"{bColors.FAIL}{statusLine}"
        print(f"Status code: {statusLine}{bColors.ENDC}")

    def mapDomain(self, url: Union[str, URL], mapSize: int = 1, sleepTime: float = 0) -> None:
        if isinstance(url, str):
            url: URL = URL(url)
        if mapSize != 0:
            domain: str = url.domain
            startIndex: int = self.currIndex + 1
            self.converse(url)
            sleep(sleepTime)
            finishIndex: int = self.currIndex
            connectionQueue: list[Connection] = []
            urlList: list[URL] = []
            # If the connection is a redirect, the connectionList will have more than one connection.
            for i in range(startIndex, finishIndex + 1):
                connection: Connection = self.connectionList[i]
                urlList.extend(getLinksFromHTML(connection.response.body))
            for url in urlList:
                if len(connectionQueue) + len(self.connectionList) > mapSize:
                    break
                if url.domain == domain and (url.scheme == "https" or url.scheme == "") and \
                        url not in self.cookieJar and not isFileUrl(url):
                    connectionQueue.append(Connection(url, 'GET', getUrlName(url)))
                    self.cookieJar.visit(url)
            for connection in connectionQueue:
                self.mapDomain(connection.url, mapSize - 1)
        if mapSize == 0:
            print(f"{bColors.OKGREEN}Done.{bColors.ENDC}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.log:
            self.__logData(self.totalData.decode("ISO-8859-1"), f"allData.txt")
        if self.__clientSocket is not None:
            self.__clientSocket.close()
