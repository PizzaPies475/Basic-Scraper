from re import sub
import httpUtil
from Cookie import Cookie
import socket
import ssl
from os import mkdir
import webbrowser
from os import getcwd
from timeit import default_timer as timer
from os import path


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
    # Also creates the folder if the path doesn't exist.
    def __init__(self, logsFolderPath: str = "HTTP-Logs", errorsFolderPath: str = "invalid_packets/", maxReferrals: int = 5, recvTimeOut: int = 3,
                 port: int = 443, listenSize: int = 4096) -> None:
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
        self.logsFolderPath: str = logsFolderPath
        self.errorsFolderPath: str = errorsFolderPath
        self.currentRequestIndex: int = 0
        self.lastReferredURL: str = ''
        self.domainCookiesDict: dict = dict()  # {domain: {cookieName: Cookie}}
        self.__securedSocket: socket = socket.socket()
        self.maxReferrals: int = maxReferrals
        self.recvTimeOut: int = recvTimeOut  # in seconds
        self.port: int = port  # Should be 443 always, but added for flexibility.
        self.requestsSent: list = []
        self.listenSize: int = listenSize

    # Initiates the connection while following the given connection list.
    # If the server redirects, it will follow the redirect up to a limit, which by default is 5.
    # If the max referrals is exceeded a value error will be raised.
    def startConversation(self, connectList: list, acceptedEnc: str = "utf-8", ignoreExceptions: bool = True) -> None:
        for i in range(len(connectList)):
            requestName: str = connectList[i][0]
            requestType: str = connectList[i][1]
            url: str = connectList[i][2]
            content: str = connectList[i][3]
            headersDict: dict = connectList[i][4]

            totalRequestName: str = f"{str(self.currentRequestIndex)}{requestName}{requestType}"
            response: tuple[str, str] = self.__converse(totalRequestName, requestType, url, content, headersDict,
                                                        acceptedEnc,
                                                        ignoreExceptions)
            responseHeaders: str = response[0]
            responseContent: str = response[1]
            self.requestsSent.append(f"{totalRequestName} {url}")
            referredCount: int = 0
            while "Location:" in responseHeaders and referredCount < self.maxReferrals:
                requestType = "GET"
                referredRequestName: str = f"{self.currentRequestIndex}{requestName}{referredCount}{requestType}"
                url: str = getReferralLink(responseHeaders)
                print(f"Referring to {url}")
                response: tuple[str, str] = self.__converse(referredRequestName, requestType, url, content, headersDict,
                                                            acceptedEnc, ignoreExceptions)
                responseHeaders: str = response[0]
                responseContent: str = response[1]
                self.requestsSent.append(f"{referredRequestName} {url} (Referred)")
                referredCount += 1
                if not referredCount < self.maxReferrals:
                    raise ValueError(f"Number of referrals exceeded: {self.maxReferrals} (given max).")

    #
    def __converse(self, requestName: str, requestType: str, url: str, content: str, headersDict: dict,
                   acceptedEnc: str, ignoreExceptions: bool) -> tuple:
        self.changeHostIfNeeded(url)
        if self.domainCookiesDict is not None and url in self.domainCookiesDict:
            checkCookies(self.domainCookiesDict[url])
        request: str = httpUtil.buildRequest(requestType, url, content=content, urlCookiesDict=self.domainCookiesDict,
                                             moreHeaders=headersDict, acceptEnc=acceptedEnc)
        (responseHeaders, responseContent) = self.sendRecvLog(request, requestName, ignoreExceptions=ignoreExceptions)
        self.getSetCookiesDomain(requestName, url)
        self.lastReferredURL: str = url
        self.currentRequestIndex += 1
        return responseHeaders, responseContent

    # Given a domain, the function will update the given dictionary (urlCookiesDict) with the cookies set by the HTTP
    #   response recorded in the requestName_response.txt file.
    # In the dictionary, each domain is mapped to a dictionary of cookieName:cookie.
    # The cookieName is a String of the name of the cookie, and cookie is the actual Cookie object.
    # So the urlCookiesDict can be summed up as: {domain: {cookieName: Cookie (object)}}.
    def getSetCookiesDomain(self, requestName: str, URL: str) -> None:
        if httpUtil.getDomainFromUrl(URL) not in self.domainCookiesDict:
            self.domainCookiesDict[httpUtil.getDomainFromUrl(URL)] = dict()
        with open(f"{self.logsFolderPath}{requestName}_headers.txt", "rb") as responseFile:
            cookiesList: list = []
            for line in responseFile:
                if "Set-Cookie:" in line.decode(encoding="ISO-8859-1"):
                    cookiesList.append(line.decode(encoding="ISO-8859-1").removeprefix("Set-Cookie: ").strip())
            for cookieLine in cookiesList:
                currentCookie: Cookie = Cookie(cookieLine, URL)
                if currentCookie.getValue() != "deleted" and not currentCookie.isExpired():
                    self.domainCookiesDict[httpUtil.getDomainFromUrl(URL)][currentCookie.getName()] = currentCookie

    # Sends the data to the given socket, receives the reply and logs the messages.
    # Does minimal parsing to the data, which separates the HTTP response from the HTTP content.
    # Logs the request sent.
    # Also logs the response, and any content sent along with the response, in bytes and as text.
    # It will save the logs to the path given to the constructor.
    # Returns the response and the content received (as a tuple).
    def sendRecvLog(self, request: str, requestName: str, ignoreExceptions: bool = True) -> (str, str):
        logDataLines: bytes = bytes()
        logData = bytes()
        hasReceivedHeaders: bool = False
        isChunked: bool = False
        headers = bytes()
        content = bytes()

        self.__securedSocket.send(request.encode())
        print(f"Sending {requestName}")
        start: float = timer()
        while True:
            # if elapsed time since the request is greater than maxRecvTime, break.
            if timer() - start > self.recvTimeOut:
                if ignoreExceptions:
                    print(f"{bcolors.WARNING}Time to receive response exceeds maxRecvTime: {self.recvTimeOut}. "
                          f"Logging message and continuing{bcolors.ENDC}")
                    break
                else:
                    httpUtil.logData(headers, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}headers.txt")
                    httpUtil.logData(content, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}_content.txt")
                    raise TimeoutError(f"Time to receive response exceeds maxRecvTime: {self.recvTimeOut}.")
            try:
                currData: bytes = self.__securedSocket.recv(self.listenSize)
                logDataLines += b"|" + currData
                logData += currData
            except TimeoutError:
                print(f"{bcolors.WARNING}Response ended on timeout and was not caught by the loop. "
                      f"Logging message and continuing.{bcolors.ENDC}")
                break
            except ssl.SSLWantReadError as e:
                if ignoreExceptions:
                    print(f"{bcolors.WARNING}Unknown failure to receive packet on request {requestName}. "
                          f"Ignoring exception.{bcolors.ENDC}")
                    continue
                else:
                    httpUtil.logData(headers, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}headers.txt")
                    httpUtil.logData(content, f"{self.logsFolderPath}{self.errorsFolderPath}{requestName}_content.txt")
                    raise e
            if hasReceivedHeaders and isChunked:
                if currData.startswith(b"0\r\n") or currData.startswith(b"0\n") or currData.startswith(b"0\r"):
                    print("Received end of chunked data.")
                    break
                content += currData
            else:
                content += currData
                endOfHeaders = content.find(b"\r\n\r\n")
                if endOfHeaders != -1:
                    hasReceivedHeaders = True
                    headers: bytes = content[:endOfHeaders]
                    content: bytes = content[endOfHeaders + 4:]
                    if b"Transfer-Encoding: chunked" in headers:
                        isChunked = True
                        print("Receiving chunked data.")
                    elif b"Content-Type:" not in headers or b"Content-Length: 0" in headers:
                        headers = content.split(b"\r\n\r\n")[0]
                        break
            if b"</html>" in content:
                print("Received end of chunked data.")
                content = content.split(b"</html>")[0] + b"</html>"
                break

        decodedContent = content.decode(encoding="ISO-8859-1")
        decodedHeaders = headers.decode(encoding="ISO-8859-1")
        if isChunked:
            subbedContent: str = sub(r"[0-9a-f]{2,4}(\r\n|\n)", "****", decodedContent)
            httpUtil.logData(subbedContent, f"{self.logsFolderPath}{requestName}_contentSubstituted.txt")
            decodedContent: str = sub(r"[0-9a-f]{2,4}(\r\n|\n)", "", decodedContent)  # Remove chunk sizes

        httpUtil.logData(logData, f"{self.logsFolderPath}{requestName}_packet.txt")
        httpUtil.logData(logDataLines, f"{self.logsFolderPath}{requestName}_packetWithLines.txt")
        httpUtil.logData(decodedHeaders, f"{self.logsFolderPath}{requestName}_headers.txt")
        if "Content-Type: text/html" in decodedHeaders:
            httpUtil.logData(decodedContent, f"{self.logsFolderPath}{requestName}_content.html")
        else:
            httpUtil.logData(decodedContent, f"{self.logsFolderPath}{requestName}_content.txt")
        return decodedHeaders, decodedContent

    # Returns a socket connected to the IP of the given URL (by dns).
    # The post of the connection is defaulted to 443 (HTTPS port).
    # If a socket is given, the connection will be closed if the host is changed.
    # Then, a new socket will be created, connected as described above, and returned.
    def changeHostIfNeeded(self, url: str, port: int = 443) -> None:
        if not httpUtil.isValidURL(url):
            raise ValueError(f"Invalid URL: {url}.")
        urlHost: str = httpUtil.getDomainFromUrl(url)
        lastHost = httpUtil.getDomainFromUrl(self.lastReferredURL)
        if self.__securedSocket is None or urlHost != lastHost:
            if self.__securedSocket is not None:
                self.__securedSocket.close()
            ip: str = socket.gethostbyname(urlHost)
            clientSocket: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__securedSocket = ssl.create_default_context().wrap_socket(clientSocket, server_hostname=urlHost)
            print(f"Connecting to address: {ip}/{port}.")
            self.__securedSocket.connect((ip, port))
            self.__securedSocket.settimeout(self.recvTimeOut)

    def showInChrome(self, requestName: str) -> None:
        filename = f"file://{getcwd()}/{self.logsFolderPath}{requestName}_content.html"
        print(f"Opening html file:{filename}.")
        webbrowser.get().open(filename, new=2)

    def printAllConnections(self) -> None:
        for connection in self.requestsSent:
            print(connection)

    def getIndex(self) -> int:
        return self.currentRequestIndex

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.__securedSocket.close()
        return False


def findEndOfRequest(HttpResponseContent: str) -> int:
    endOfRequest = 0
    HttpResponseLen = len(HttpResponseContent)
    while endOfRequest in range(HttpResponseLen):
        endLineCount = 0
        currEncodedLetter = HttpResponseContent[endOfRequest].encode()
        while endOfRequest < HttpResponseLen and (
                currEncodedLetter == '\r'.encode() or currEncodedLetter == '\n'.encode()) and endLineCount < 3:
            endLineCount += 1
            endOfRequest += 1
            currEncodedLetter = HttpResponseContent[endOfRequest].encode()
        if endLineCount == 3:
            return endOfRequest
        endOfRequest += 1
    return endOfRequest


# Returns the referral url given by the host in the Location HTTP header.
def getReferralLink(data: str) -> str:
    locationStart = data.find("Location: ")
    locationEnd = data[locationStart:].find("\r\n")
    url = data[locationStart:locationStart + locationEnd].removeprefix("Location: ")
    return url


# Checks if the cookies in the given dictionary are valid.
# A valid cookie means that it is not expired and not deleted explicitly by the host.
# If a cookie is invalid it deletes it.
def checkCookies(cookiesDict: dict) -> None:
    for cookieName in cookiesDict:
        if cookiesDict[cookieName].isExpired() or cookiesDict[cookieName].getValue() == "deleted":
            del cookiesDict[cookieName]
