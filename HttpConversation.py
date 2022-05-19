from re import sub
import httpUtil
from Cookie import Cookie
from socket import socket, gethostbyname, AF_INET, SOCK_STREAM, gaierror
from socket import error as socket_error
import webbrowser
from os import getcwd, mkdir
from timeit import default_timer as timer
from ssl import SSLWantReadError, create_default_context, SSLEOFError
from Connection import Connection
from typing import Union
from queue import Queue
from DomainTree import DomainTree
from time import sleep


class bcolors:
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
    """
    This class is used to handle the conversation between the client and the server.
    To use it, you need to create an instance of it and call the method "startConversation".
    """

    def __init__(self, logsFolderPath: str = "HTTP-Logs", errorsFolderPath: str = "invalid_packets/",
                 maxReferrals: int = 5, packetRecvTimeOut: int = 2, responseRecvTimeOut: int = 2, port: int = 443,
                 listenSize: int = 4096):
        """
        :param logsFolderPath: The path to the folder where the logs will be saved.
        :param errorsFolderPath: The path to the folder where the invalid packets will be saved.
        :param maxReferrals:
        :param packetRecvTimeOut: in seconds
        :param responseRecvTimeOut: in seconds
        :param port: Should be 443 always, added for flexibility
        :param listenSize: The size of the buffer to be used when receiving data from the socket.
        """

        self.logsFolderPath: str = logsFolderPath
        self.errorsFolderPath: str = errorsFolderPath
        if logsFolderPath == '' or logsFolderPath is None:
            logsFolderPath = "HTTP-Logs/"
        if errorsFolderPath == '' or errorsFolderPath is None:
            errorsFolderPath = "invalid_packets/"
        try:
            mkdir(logsFolderPath)
        except FileExistsError:
            pass
        try:
            mkdir(f"{logsFolderPath}{errorsFolderPath}")
        except FileExistsError:
            pass
        self.currentRequestIndex: int = 0
        self.lastReferredURL: str = ''
        self.domainCookiesDict: {str: {str: Cookie}} = dict()  # {domain: {path: Cookie}}
        self.__securedSocket: socket = socket()
        self.maxReferrals: int = maxReferrals
        self.packetRecvTimeOut: int = packetRecvTimeOut
        self.responseRecvTimeOut: int = responseRecvTimeOut
        self.port: int = port
        self.requestsSent: dict = dict()
        self.listenSize: int = listenSize
        self.currConnection: Connection = Connection("", "", "")

    def startConversation(self, connections: Union[list[Connection], Connection], acceptedEnc: str = "utf-8",
                          ignoreExceptions: bool = True, options: bool = False) -> None:
        if not isinstance(connections, list):
            connections = [connections]
        shouldClose: bool = False
        for i in range(len(connections)):
            self.currConnection = connections[i]
            response: tuple[str, str] = self.__converse(shouldClose, acceptedEnc, ignoreExceptions, options=options)
            responseHeaders: str = response[0]
            #  responseBody: str = response[1]
            if "Connection: close" in responseHeaders or "connection: close" in responseHeaders:
                shouldClose = True
            referredCount: int = 0
            while "Location:" in responseHeaders and referredCount < self.maxReferrals:
                URL, referer = getReferralLink(responseHeaders, httpUtil.getDomainFromUrl(self.currConnection.URL))
                self.currConnection: Connection = Connection(f"{self.currConnection}{referredCount}referred", 'GET',
                                                             URL)
                print(f"Referring to {URL}")
                response: tuple[str, str] = self.__converse(shouldClose, acceptedEnc=acceptedEnc,
                                                            ignoreExceptions=ignoreExceptions, referer=referer,
                                                            options=options)
                responseHeaders: str = response[0]
                #  responseBody: str = response[1]
                referredCount += 1
                if not referredCount < self.maxReferrals:
                    raise ValueError(f"Number of referrals exceeded: {self.maxReferrals} (given max).")

    def mapDomain(self, domain: Union[str, Connection], log: bool = False, acceptedEnc: str = "utf-8",
                  options: bool = False) -> tuple:
        connectionQueue: Queue[Connection] = Queue()
        baseCategories: list[str] = ["External", "Images", "Videos", "Music", "scripts", "CSS", "JS", "Json", "Fonts",
                                     "Queries"]
        categories: {str: list[str]} = {"External": [], "Files": []}
        domainTree: DomainTree = DomainTree(domain)
        externalUrls: dict = {}
        shouldClose = False
        if isinstance(domain, str):
            if httpUtil.isValidURL(domain):
                domainName = httpUtil.getDomainName(domain)
                domain: Connection = Connection(domainName, 'GET', domain)
            else:
                raise ValueError(f"{domain} is not a valid URL.")
        connectionQueue.put(domain)
        while not connectionQueue.empty():
            self.currConnection = connectionQueue.get()
            response: tuple[str, str] = self.__converse(shouldClose, acceptedEnc, log=log, options=options, ignoreExceptions=True)
            responseHeaders: str = response[0]
            responseBody: str = response[1]
            linksList: list[str] = httpUtil.getLinksFromHTML(responseBody)
            for link in linksList:
                if not httpUtil.isValidURL(link):
                    raise ValueError(f"({link}) is not a valid URL.")
                if httpUtil.isSameOrigin(link, domain.URL) and not httpUtil.isFileUrl(link) and link not in self.requestsSent:
                    connectionName = httpUtil.getDomainName(link)
                    domainTree.put(link)
                    connectionQueue.put(Connection(connectionName, 'GET', link))
                elif httpUtil.isFileUrl(link):
                    categories["Files"].append(link)
                if not httpUtil.isSameOrigin(link, domain.URL):
                    categories["External"].append(link)
            if "Connection: close" in responseHeaders or "connection: close" in responseHeaders:
                shouldClose = True
            referredCount: int = 0
            while "Location:" in responseHeaders and referredCount < self.maxReferrals:
                URL, referer = getReferralLink(responseHeaders, httpUtil.getDomainFromUrl(self.currConnection.URL))
                self.currConnection: Connection = Connection(f"{self.currConnection}{referredCount}", 'GET',
                                                             URL)
                isReferred = True
                print(f"Referring to {URL}")
                response: tuple[str, str] = self.__converse(shouldClose, acceptedEnc=acceptedEnc, referer=referer,
                                                            options=options, log=log, referred=isReferred, ignoreExceptions=True)
                responseHeaders: str = response[0]
                responseBody: str = response[1]
                linksList: list[str] = httpUtil.getLinksFromHTML(responseBody)
                for link in linksList:
                    if not httpUtil.isValidURL(link):
                        raise ValueError(f"({link}) is not a valid URL.")
                    if httpUtil.isSameOrigin(link, domain.URL) and not httpUtil.isFileUrl(link):
                        connectionName = httpUtil.getDomainName(link)
                        domainTree.put(link)
                        connectionQueue.put(Connection(connectionName, 'GET', link))
                    elif httpUtil.isFileUrl(link):
                        categories["Files"].append(link)
                    else:
                        categories["External"].append(link)
                if "Connection: close" in responseHeaders or "connection: close" in responseHeaders:
                    shouldClose = True
                referredCount += 1
                if not referredCount < self.maxReferrals:
                    raise ValueError(f"Number of referrals exceeded: {self.maxReferrals} (given max).")
        return domainTree, categories

    def __converse(self, shouldClose: bool, acceptedEnc: str = 'utf-8', ignoreExceptions: bool = True, log: bool = True,
                   referer: str = "", options: bool = False, referred: bool = False, isError: bool = False) -> tuple[str, str]:

        if self.currConnection.URL in self.requestsSent:
            if ignoreExceptions:
                return "", ""
            else:
                raise ValueError(f"Request already sent: {self.currConnection.URL}")

        self.__changeHostIfNeeded(shouldClose)
        if self.domainCookiesDict is not None and self.currConnection.URL in self.domainCookiesDict:
            checkCookies(self.domainCookiesDict[self.currConnection.URL])
        request: str = httpUtil.buildRequest(self.currConnection.requestType, self.currConnection.URL,
                                             content=self.currConnection.content, urlCookiesDict=self.domainCookiesDict,
                                             moreHeaders=self.currConnection.headers, acceptEnc=acceptedEnc,
                                             referer=referer, options=options)
        responseHeaders, responseBody = self.sendRecvLog(request, ignoreExceptions=ignoreExceptions, log=log,
                                                         referred=referred, isError=isError)
        self.requestsSent[self.currConnection.URL] = self.currConnection.URL
        self.getSetCookiesDomain(responseHeaders)
        self.lastReferredURL: str = self.currConnection.URL
        self.currentRequestIndex += 1
        sleep(0.5)
        return responseHeaders, responseBody

    def getSetCookiesDomain(self, responseHeaders: str) -> None:
        URL = self.currConnection.URL
        if httpUtil.getDomainFromUrl(URL) not in self.domainCookiesDict:
            self.domainCookiesDict[httpUtil.getDomainFromUrl(URL)] = dict()
        responseLines = responseHeaders.split("\r\n")
        cookiesList: list = []
        for header in responseLines:
            if "Set-Cookie:" in header or "set-cookie:" in header:
                cookiesList.append(header.removeprefix("Set-Cookie: ").removeprefix("set-cookie: ").strip())
        for cookieLine in cookiesList:
            currentCookie: Cookie = Cookie(cookieLine, URL)
            if currentCookie.getValue() != "deleted" and not currentCookie.isExpired():
                self.domainCookiesDict[httpUtil.getDomainFromUrl(URL)][currentCookie.getName()] = currentCookie

    # Sends the data to the given socket, receives the reply and logs the messages.
    # Does minimal parsing to the data, which separates the HTTP response from the HTTP body.
    # Logs the request sent.
    # Also logs the response, and any content sent along with the response, in bytes and as text.
    # It will save the logs to the path given to the constructor.
    # Returns the headers and the body as a tuple.
    def sendRecvLog(self, request: str, ignoreExceptions: bool = True, log: bool = True,
                    referred: bool = False, isError: bool = False) -> (str, str):
        requestName = f"{self.currentRequestIndex}{self.currConnection}"
        requestType: str = self.currConnection.requestType
        if referred:
            requestName += "referred"
        logDataLines: bytes = bytes()
        logDataAsIs = bytes()
        hasReceivedHeaders: bool = False
        isChunked: bool = False
        headers = bytes()
        body = bytes()

        try:
            self.__securedSocket.send(request.encode())
        except SSLEOFError:
            if ignoreExceptions and not isError:
                print(f"{bcolors.WARNING}Error on request to: {self.currConnection.URL} {bcolors.ENDC}")
                return self.__converse(True, ignoreExceptions=ignoreExceptions, log=log, referred=referred)
            else:
                requestFileName: str = f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}_request.txt"
                httpUtil.logData(request, requestFileName)
                raise SSLEOFError(f"Could not send request to: {self.currConnection.URL}. "
                                  f"Request logged at: {requestFileName}.")
        httpUtil.logData(request, f"{self.logsFolderPath}{requestName}{requestType}_request.txt", log=log)
        print(f"Sending {requestName}")
        start: float = timer()
        while True:
            if timer() - start > self.responseRecvTimeOut:
                if ignoreExceptions:
                    print(f"{bcolors.WARNING}"
                          f"Time to receive response exceeds responseRecvTimeOut: {self.responseRecvTimeOut}. "
                          f"Logging message and continuing."
                          f"{bcolors.ENDC}")
                    break
                else:
                    httpUtil.logData(headers, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}{requestType}_headers.txt")
                    httpUtil.logData(body, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}{requestType}_body.txt")
                    raise TimeoutError(f"Time to receive response exceeds maxRecvTime: {self.responseRecvTimeOut}.")
            try:
                currData: bytes = self.__securedSocket.recv(self.listenSize)
                logDataLines += b"|" + currData
                logDataAsIs += currData
            except TimeoutError:
                print(f"{bcolors.WARNING}Response ended on timeout and was not caught by the loop. "
                      f"Logging message and continuing.{bcolors.ENDC}")
                break
            except SSLWantReadError as e:
                if ignoreExceptions:
                    print(f"{bcolors.WARNING}Unknown failure to receive packet on request {requestName}. "
                          f"Ignoring exception.{bcolors.ENDC}")
                    continue
                else:
                    httpUtil.logData(headers, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}{requestType}_headers.txt",
                                     log)
                    httpUtil.logData(body, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}{requestType}_body.txt", log)
                    raise e
            if hasReceivedHeaders and isChunked:
                if currData.startswith(b"0\r\n") or currData.startswith(b"0\n") or currData.startswith(b"0\r"):
                    print("Received end of chunked data.")
                    break
                body += currData
            else:
                body += currData
                endOfHeaders: int = body.find(b"\r\n\r\n")
                if endOfHeaders != -1:
                    hasReceivedHeaders = True
                    headers: bytes = body[:endOfHeaders]
                    body: bytes = body[endOfHeaders + 4:]
                    if b"Transfer-Encoding: chunked" in headers or b"Transfer-Encoding:  chunked" in headers or \
                            b"transfer-encoding: chunked" in headers or b"transfer-encoding:  chunked" in headers:
                        isChunked = True
                        print("Receiving chunked data.")
                    elif b"Content-Type:" not in headers or b"Content-Length: 0" in headers:
                        break
            if b"</html>" in body:
                print("Received end of chunked data.")
                rest = b"".join(body.split(b"</html>")[1:])
                httpUtil.logData(rest, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}{requestType}_remainder.txt", log)
                body = body.split(b"</html>")[0] + b"</html>"
                break

        decodedBody: str = body.decode(encoding="ISO-8859-1")
        decodedHeaders: str = headers.decode(encoding="ISO-8859-1")
        if isChunked:
            subbedBody: str = sub(r"[0-9a-fA-F]{2,8}(\r\n|\n)", "****", decodedBody)
            httpUtil.logData(subbedBody, f"{self.logsFolderPath}{requestName}{requestType}_bodySubstituted.txt", log)
            decodedBody: str = sub(r"[0-9a-fA-F]{2,8}(\r\n|\n)", "", decodedBody)  # Remove chunk sizes

        httpUtil.logData(logDataAsIs, f"{self.logsFolderPath}{requestName}{requestType}_packet.txt", log)
        httpUtil.logData(logDataLines, f"{self.logsFolderPath}{requestName}{requestType}_packetWithLines.txt", log)
        httpUtil.logData(decodedHeaders, f"{self.logsFolderPath}{requestName}{requestType}_headers.txt", log)
        if "Content-Type: text/html" in decodedHeaders or "content-type: text/html" in decodedHeaders:
            httpUtil.logData(decodedBody, f"{self.logsFolderPath}{requestName}{requestType}_body.html", log)
        else:
            httpUtil.logData(decodedBody, f"{self.logsFolderPath}{requestName}{requestType}_body.txt", log)
        return decodedHeaders, decodedBody

    # Returns a socket connected to the IP of the given URL (by dns).
    # The post of the connection is defaulted to 443 (HTTPS port).
    # If a socket is given, the connection will be closed if the host is changed.
    # Then, a new socket will be created, connected as described above, and returned.
    def __changeHostIfNeeded(self, shouldClose: bool) -> None:
        if not httpUtil.isValidURL(self.currConnection.URL):
            if "referred" in self.currConnection.name:
                raise ValueError(f"The referred URL is not valid: {self.currConnection.URL}")
            raise ValueError(f"Invalid URL: {self.currConnection.URL}.")
        urlHost: str = httpUtil.getDomainFromUrl(self.currConnection.URL)
        lastHost: str = httpUtil.getDomainFromUrl(self.lastReferredURL)
        if self.__securedSocket is None or urlHost != lastHost or shouldClose:
            if self.__securedSocket is not None or shouldClose:
                self.__securedSocket.close()
            try:
                ip: str = gethostbyname(urlHost)
            except gaierror:
                raise ValueError(f"Could not resolve host: {urlHost}.")
            clientSocket: socket = socket(AF_INET, SOCK_STREAM)
            self.__securedSocket = create_default_context().wrap_socket(clientSocket, server_hostname=urlHost)
            print(f"Connecting to address: {ip}/{self.port}.")
            self.__securedSocket.connect((ip, self.port))
            self.__securedSocket.settimeout(self.packetRecvTimeOut)

    def showInChrome(self, requestName: str) -> None:
        filename = f"file://{getcwd()}/{self.logsFolderPath}{requestName}_body.html"
        print(f"Opening html file:{filename}.")
        webbrowser.get().open(filename, new=2)

    def printAllConnections(self) -> None:
        for connection in self.requestsSent:
            print(connection)

    def getIndex(self) -> int:
        return self.currentRequestIndex

    def getCurrConnectionName(self) -> str:
        return f"{self.currentRequestIndex - 1}{self.currConnection}"

    def getCookies(self) -> {str: {str: Cookie}}:
        return self.domainCookiesDict

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            self.__securedSocket.close()
        except socket_error:
            pass
        return False


# Returns the referral url given by the host in the Location HTTP header.
def getReferralLink(data: str, domain: str) -> tuple[str, str]:
    referer: str = ""
    locationStart: int = data.find("Location: ")
    locationEnd = data[locationStart:].find("\r\n")
    url = data[locationStart:locationStart + locationEnd].removeprefix("Location: ")
    referrerPolicyStart: int = data.find("Referrer-Policy: ")
    if referrerPolicyStart != -1:
        referrerPolicyEnd: int = data[referrerPolicyStart:].find("\r\n")
        refererPolicy: str = data[referrerPolicyStart:referrerPolicyStart + referrerPolicyEnd].removeprefix(
            "Referrer-Policy: ")
        if refererPolicy == "no-referrer":
            referer = ""
        elif refererPolicy == "no-referrer-when-downgrade":
            referer = domain
        elif refererPolicy == "origin":
            referer = httpUtil.getDomainFromUrl(domain)
        elif refererPolicy == "origin-when-cross-origin":
            if httpUtil.isSameOrigin(domain, url):
                referer = domain
            else:
                referer = httpUtil.getDomainFromUrl(domain)
        elif refererPolicy == "same-origin":
            if httpUtil.isSameOrigin(domain, url):
                referer = url
        elif refererPolicy == "strict-origin":
            referer = httpUtil.getDomainFromUrl(domain)
    else:
        if httpUtil.isSameOrigin(domain, url):
            referer = url
        else:
            referer = httpUtil.getDomainFromUrl(domain)
    if url.startswith('/'):
        url = f"{domain}{url}"
    return url, referer


# Checks if the cookies in the given dictionary are valid.
# A valid cookie means that it is not expired and not deleted explicitly by the host.
# If a cookie is invalid it deletes it.
def checkCookies(cookiesDict: dict) -> None:
    for cookieName in cookiesDict:
        if cookiesDict[cookieName].isExpired() or cookiesDict[cookieName].getValue() == "deleted":
            del cookiesDict[cookieName]
