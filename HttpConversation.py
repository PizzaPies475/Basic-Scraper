import httpUtil
from Cookie import Cookie
import socket
import ssl
import generalUtils
from os import mkdir
from webbrowser import open_new_tab
from os import getcwd
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
    # Also creates the folder if the path doesn't exist.
    def __init__(self, logsFolderPath: str = "HTTP-Logs", maxReferrals: int = 5, recvTimeOut: int = 1,
                 port: int = 443) -> None:
        if logsFolderPath == '':
            logsFolderPath = "HTTP-Logs/"
        try:
            mkdir(logsFolderPath)
        except FileExistsError:
            pass
        try:
            mkdir(f"{logsFolderPath}invalid_packets/")
        except FileExistsError:
            pass
        self.logsFolderPath: str = logsFolderPath
        self.currentRequestIndex: int = 0
        self.lastReferredURL: str = ''
        self.domainCookiesDict: dict = dict()
        self.__securedSocket: socket = socket.socket()
        self.maxReferrals: int = maxReferrals
        self.recvTimeOut: int = recvTimeOut
        self.port: int = port
        self.requestsSent: list = []

    # Initiates the connection while following the given connection list.
    # If the server redirects, it will follow the redirect up to a limit, which by default is 5.
    # If the max referrals is exceeded a value error will be raised.
    def startConversation(self, connectList: list, acceptedEnc: str = "utf-8") -> None:
        for i in range(len(connectList)):
            requestName: str = connectList[i][0]
            requestType: str = connectList[i][1]
            url: str = connectList[i][2]
            content: str = connectList[i][3]
            headersDict: dict = connectList[i][4]
            totalRequestName: str = f"{str(self.currentRequestIndex)}{requestName}{requestType}"
            (responseHeaders, responseContent) = self.__converse(totalRequestName, requestType, url, content,
                                                                 headersDict,
                                                                 acceptedEnc)
            self.requestsSent.append(f"{totalRequestName} {url}")
            referredCount: int = 0
            while "Location:" in responseHeaders and referredCount < self.maxReferrals:
                requestType = "GET"
                referredRequestName: str = f"{self.currentRequestIndex}{requestName}{referredCount}{requestType}"
                url: str = getReferralLink(responseHeaders)
                print(f"Referring to {url}")
                (responseHeaders, responseContent) = self.__converse(referredRequestName, requestType, url, content,
                                                                     headersDict, acceptedEnc)
                self.requestsSent.append(f"{referredRequestName} {url} (Referred)")
                referredCount += 1
                if not referredCount < self.maxReferrals:
                    raise ValueError(f"Number of referrals exceeded: {self.maxReferrals} (given max).")

    #
    def __converse(self, requestName: str, requestType: str, url: str, content: str, headersDict: dict,
                   acceptedEnc: str):
        self.changeHostIfNeeded(url)
        if self.domainCookiesDict is not None and url in self.domainCookiesDict:
            checkCookies(self.domainCookiesDict[url])
        request: str = httpUtil.buildRequest(requestType, url, content=content, urlCookiesDict=self.domainCookiesDict,
                                             moreHeaders=headersDict, acceptEnc=acceptedEnc)
        (responseHeaders, responseContent) = self.sendRecvLogData(request, requestName)
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
        with open(f"{self.logsFolderPath}{requestName}_response.txt", "rb") as responseFile:
            cookiesList: list = []
            for line in responseFile:
                if "Set-Cookie:" in line.decode(encoding="ISO-8859-1"):
                    cookiesList.append(line.decode(encoding="ISO-8859-1").removeprefix("Set-Cookie: ").strip())
            for cookieLine in cookiesList:
                currentCookie: Cookie = Cookie(cookieLine, URL)
                if currentCookie.getValue() != "deleted" and not currentCookie.isExpired():
                    self.domainCookiesDict[httpUtil.getDomainFromUrl(URL)][currentCookie.getName()] = currentCookie

    # Send the request and receive the response or the beginning of it.
    # If an error occurs, the client will try and resend the request.
    # Returns the data received to be used by sendRecv.
    def initialSendRecv(self, request: str, requestName: str, listenSize: int = 32768, maxRecv: int = 10,
                        retries: int = 5) -> bytes:
        recvCount: int = 0
        self.__securedSocket.send(request.encode())
        data: bytes = bytes()
        try:
            data = self.__securedSocket.recv(listenSize)
            a = 1
        except ssl.SSLWantReadError:
            print(
                f"{bcolors.WARNING}Unknown failure to receive packet on request {requestName}. Retrying.{bcolors.ENDC}")
            return self.initialSendRecv(request, requestName, retries=retries - 1)
        except TimeoutError:
            print(f"{bcolors.WARNING}Timeout on request {requestName}. Retrying.{bcolors.ENDC}")
            return self.initialSendRecv(request, requestName, retries=retries - 1)
        # The server might send empty or otherwise failed packets for unknown reasons.
        # If so, the client will try and receive packets for maxRecv times.
        # If exceeded, the client will try and send the request again.
        while not httpUtil.isValidResponse(data) and retries != 0:
            generalUtils.clearFileAndWrite(
                f"{self.logsFolderPath}invalid_packets/{requestName}{recvCount}_packetLog.txt", 'wb', data)
            if recvCount > maxRecv:
                print(
                    f"{bcolors.WARNING}Number of invalid packets exceeds maximum ({str(maxRecv)}). Retrying to send.{bcolors.ENDC}")
                return self.initialSendRecv(request, requestName, retries=retries - 1)
            try:
                data = self.__securedSocket.recv(listenSize)
            except TimeoutError:
                pass
            recvCount += 1
        else:
            if retries == 0 and not httpUtil.isValidResponse(data):
                raise Exception(f"Unable to receive response ")
            if not data.endswith(b'\r\n\r\n'):
                return self.initialSendRecv(request, requestName, retries=retries - 1)
        return data

    def initialSendRecv2(self, request: str, requestName: str, listenSize: int = 4096, maxRecv: int = 100000) -> bytes:
        self.__securedSocket.send(request.encode())
        data = self.__securedSocket.recv(listenSize)
        logData = data
        while not data.endswith(b'\r\n\r\n') and maxRecv != 0:
            try:
                currData = self.__securedSocket.recv(listenSize)
            except TimeoutError:
                return data
            data += currData
            logData += b"|" + currData
            maxRecv -= 1
        if maxRecv == 0:
            print(f"{bcolors.WARNING}Unable to receive full response {requestName}. Limit exceeded.{maxRecv}{bcolors.ENDC}")
        while not data.endswith(b'\r\n\r\n') and maxRecv != 0:
            try:
                currData = self.__securedSocket.recv(listenSize)
                data += currData
                logData += b"|" + currData

        return data

    # Sends the data to the given socket, receives the reply and logs the messages.
    # Does minimal parsing to the data, which separates the HTTP response from the HTTP content.
    # Logs the request sent.
    # Also logs the response, and any content sent along with the response, in bytes and as text.
    # It will save the logs to the path given to the constructor.
    # Returns the response and the content received (as a tuple).
    def sendRecvLogData(self, request: str, requestName: str, maxNumberOfPackets: int = 40, listenSize: int = 32768,
                        maxRecv: int = 10) -> (list, list):
        print(f"Handling request: {requestName}")
        generalUtils.clearFileAndWrite(f"{self.logsFolderPath}{requestName}_request.txt", 'a', request)  # Request log
        data: bytes = self.initialSendRecv2(request, requestName, maxRecv)
        dataPackets: bytes = data + "\r\n----------------\r\n".encode()

        print("Received response.")
        httpResponseContent: str = data.decode(encoding="ISO-8859-1")
        endOfRequest: int = findEndOfRequest(httpResponseContent)
        httpResponseHeaders: str = httpResponseContent[:endOfRequest - 3]
        httpResponseLines: list[str] = httpResponseHeaders.split("\r\n")
        isChunked: bool = False

        for i in range(len(httpResponseLines) - 1, -1, -1):
            currentHeader: list[str] = httpResponseLines[i].split(':')
            if currentHeader[0].lower() == "transfer-encoding" and "chunked" in currentHeader[1].lower():
                print("Receiving chunked data:")
                isChunked = True
                break
        # Data that is going to be received is chunked and the client will wait until all chunks are received.
        if isChunked:
            decodedContent: str = httpResponseContent[endOfRequest + 7:]
        # Means that there is additional data with the packet.
        elif len(httpResponseContent) - endOfRequest > 6:
            decodedContent = httpResponseContent[endOfRequest:].removeprefix('\r\n')
        # Means that no data was received from the server, other than the HTTP response.
        else:
            decodedContent = ""
        if isChunked:
            i = 1
            while i in range(1, maxNumberOfPackets):
                try:
                    currData = self.__securedSocket.recv(listenSize)
                except TimeoutError:
                    break
                while currData == ''.encode():
                    print("Received empty packet.")
                    break
                else:
                    print("Received chunk:", i)
                    data += currData
                    dataPackets += currData + "\r\n----------------\r\n".encode()
                if currData.decode(encoding="ISO-8859-1").strip('\r\n') == '0':
                    pass
                else:
                    decodedContent: str = connectData(decodedContent, currData.decode(encoding="ISO-8859-1"))
                if "</html>" in decodedContent:
                    break
                i += 1
        generalUtils.clearFileAndWrite(f"{self.logsFolderPath}{requestName}_raw.txt", "wb",
                                       data)  # Reply log in bytes
        generalUtils.clearFileAndWrite(f"{self.logsFolderPath}{requestName}_rawPackets.txt", "wb",
                                       dataPackets)  # Reply log in bytes
        generalUtils.clearFileAndWrite(f"{self.logsFolderPath}{requestName}_response.txt", 'a',
                                       httpResponseHeaders)  # Response log
        if decodedContent != '':
            generalUtils.clearFileAndWrite(f"{self.logsFolderPath}{requestName}_responseContent.html", 'a',
                                           decodedContent)  # Response content log TODO Fix the data cutting.
        sleep(0.5)
        return httpResponseHeaders, decodedContent

    # Returns a socket connected to the IP of the given URL (by dns).
    # The post of the connection is defaulted to 443 (HTTPS port).
    # If a socket is given, the connection will be closed if the host is changed.
    # Then, a new socket will be created, connected as described above, and returned.
    def changeHostIfNeeded(self, url: str, port: int = 443) -> None:
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
        filename = f"file:///{getcwd()}/{self.logsFolderPath}/{requestName}_responseContent.html"
        print(f"Opening file: {filename}")
        open_new_tab(filename)

    def printAllConnections(self) -> None:
        for connection in self.requestsSent:
            print(connection)

    # Returns the current packet index of the conversation.
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


# Connects two parts of chunked data from HTTP packets.
# Removes the 4 hex digits from the beginning of the chunk which indicates the size of the incoming packet.
# Also removes unneeded \r\n.
# TODO Fix the data cutting.
def connectData(oldData: str, newData: str) -> str:
    try:
        sizeLine = newData.split('\r\n')[0]
        length = int(sizeLine, 16)  # This if for the try statement.
        if newData[len(sizeLine):len(sizeLine) + 2].encode() == "\r\n".encode():
            oldData = oldData.removesuffix("\r\n") + newData[7:]
    except ValueError:
        oldData = oldData.removesuffix("\r\n") + newData.removeprefix("\r\n")
    return oldData


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
