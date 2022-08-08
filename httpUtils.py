from datetime import datetime, timedelta
from re import match, findall, sub
from typing import Union

validUrlRegex = r"^^(([a-zA-Z]+):\/\/)?([a-zA-Z0-9_%-]+(\.[a-zA-Z0-9_%-]+)+)(:(\d+))?((\/[\w%,-]*(\.\w+)*(\?\w+(=[\w%\.,+-]+)?)?([&|;]\w*(=[\w%\.,-]+)?)*)*)(#([:~=\w%?-]+))?$"
toFindUrlRegex = r"((([a-zA-Z]+):\/\/)([a-zA-Z0-9_%-]+(\.[a-zA-Z0-9_%-]+)+)(:(\d+))?(\/[\w%,-]*(\.\w+)*(\?\w+(=[\w%+\.]+)?)?([&;]\w*(=[\w%\.,-]+)?)*)*(#[\w%]*)?)|(([a-zA-Z0-9_%-]+(\.[a-zA-Z0-9_%-]+)+)(:(\d+))?(\/[\w%,-]*(\.\w+)*(\?\w+(=[\w%+\.]+)?)?([&;]\w*(=[\w%\.,-]+)?)*)+(#[\w%]*)?)"
validPathRegex = r"^(\/[\w%?&,\.=+;-]*)*$"
validCookieRegex = r"^([\\\w~-]+)=([\\\w%-]+)((; [\\\w-]+(=[.\\\w, :\\\/?-]+)?)*)$"
findCookieAttributesRegex = r"(; ([\w-]+)(=([.\w, :\/-]+))?)"


class UrlPath:

    def __init__(self, pathList: [str]):
        self.pathList: [str] = pathList

    def __bool__(self):
        return bool(self.pathList)

    def __str__(self):
        return f"/{'/'.join(self.pathList)}"

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.pathList)

    def __eq__(self, other):
        return self.pathList == other.pathList

    def __hash__(self):
        return hash(self.pathList)

    def __getitem__(self, index):
        return self.pathList[index]


def parsePath(urlStr: str) -> UrlPath:
    urlNoHttps: str = urlStr.removeprefix("https://")
    urlNoHttps = urlNoHttps.removeprefix("http://")
    if '/' in urlNoHttps:
        pathStr: str = f"/{'/'.join(urlNoHttps.split('/')[1:])}"
    else:
        pathStr: str = "/"
    if not match(validPathRegex, pathStr):
        raise ValueError(f"Invalid path: {pathStr}")
    newPathStr: str = pathStr
    if pathStr.startswith("/"):
        newPathStr: str = newPathStr[1:]
    pathList: [str] = newPathStr.split("/")
    if pathStr.endswith("/"):
        pathList = pathList[:-1]
    return UrlPath(pathList)


class URL:

    def __init__(self, urlStr: str):
        urlMatch = match(validUrlRegex, urlStr)
        if not urlMatch:
            raise ValueError(f"Invalid URL- {urlStr}")
        self.urlStr: str = urlStr
        self.scheme: str = "" if urlMatch.group(2) is None else urlMatch.group(2)
        self.domain: str = urlMatch.group(3)
        self.port: str = "" if urlMatch.group(6) is None else urlMatch.group(6)
        self.path: UrlPath = parsePath(urlMatch.group(7))
        self.fragment: str = "" if urlMatch.group(15) is None else urlMatch.group(15)

    def fullUrlStr(self) -> str:
        return f"{self.getSchemeStr()}{self.domain}{self.getPortStr()}{self.path}{self.getFragmentStr()}"

    def getSchemeStr(self) -> str:
        return f"{self.scheme}://" if self.scheme else ""

    def getPortStr(self) -> str:
        return f":{self.port}" if self.port else ""

    def getFragmentStr(self) -> str:
        return f"#{self.fragment}" if self.fragment else ""

    def __str__(self):
        return f"{self.getSchemeStr()}{self.domain}{self.path}"

    def __repr__(self):
        return f"{self.scheme}{self.domain}{self.path}"

    def __eq__(self, other):
        return self.domain == other.domain and self.port == other.port and \
               self.path == other.path

    def __hash__(self):
        return hash(self.fullUrlStr())


def getQueriesFromUrl(urlStr: str) -> [str]:  # TODO not tested!
    return findall(r"\?([^\s/?]*)", urlStr)


class Cookie:
    def __init__(self, cookieName: str, cookieValue: str, domain: str, cookieAttributes: dict[str] = None):
        if cookieAttributes is None:
            cookieAttributes: dict[str] = dict()
        self.domain: str = domain
        self.name: str = cookieName
        self.value: str = cookieValue
        self.attributes: dict[str] = cookieAttributes

    def getAttribute(self, attribute: str):
        if attribute in self.attributes:
            return self.attributes[attribute]

    # Returns True if the current time is later than the 'expires' attribute value
    #   (which is formatted as HTTP time, see getCurrHttpTime comment in httpUtil) of the given cookie.
    # If the cookie doesn't have an 'expires' attribute, the function returns False (duh).
    def isExpired(self) -> bool:
        if self.getAttribute("expires"):
            return datetime.strptime(self.getAttribute("expires"), "%a, %d-%b-%Y %H:%M:%S GMT") < datetime.now()
        else:
            return False

    def fullCookieStr(self) -> str:
        fullStr = f"{self.name}={self.value}"
        for attribute in self.attributes:
            if self.attributes[attribute] == True:
                fullStr += f"; {attribute}"
            else:
                fullStr += f"; {attribute}={self.attributes[attribute]}"
        return fullStr

    def __str__(self):
        return f"{self.name}={self.value}"

    def __repr__(self):
        return f"{self.name}={self.value[:30]}"


def parseCookie(cookieStr: str, domain: str) -> Cookie:
    cookieMatchObject = match(validCookieRegex, cookieStr)
    if not cookieMatchObject:
        raise ValueError(f"Invalid cookie string: {cookieStr}")
    cookieName: str = cookieMatchObject.group(1)
    cookieValue: str = cookieMatchObject.group(2)
    cookieAttributes: dict[str] = dict()
    maxAgeFlag = False
    for attribute in findall(findCookieAttributesRegex, cookieMatchObject.group(3)):
        attributeName: str = attribute[1].lower()
        attributeValue = attribute[3]
        if attributeValue == "":
            attributeValue = True
        if attributeName == "max-age":
            maxAgeFlag = True
            maxAgeDate: datetime = datetime.now() + timedelta(seconds=int(attributeValue))
            cookieAttributes["expires"] = maxAgeDate.strftime(
                "%a, %d-%b-%Y %H:%M:%S GMT")  # TODO decide if this should be a datetime object and not text
        elif attributeName == "expires" and not maxAgeFlag:
            cookieAttributes["expires"] = attributeValue
        elif attributeName == "path":
            try:
                cookieAttributes["path"] = parsePath(attributeValue)
            except ValueError:
                cookieAttributes["path"] = parsePath("/")
        else:
            cookieAttributes[attributeName] = attributeValue

    if "path" not in cookieAttributes:
        cookieAttributes["path"] = parsePath("/")
    return Cookie(cookieName, cookieValue, domain, cookieAttributes)


class CookieJarNode:
    def __init__(self, name: str):
        self.name: str = name
        self.cookies: [Cookie] = []
        self.children: dict[str, CookieJarNode] = dict()
        self.parent: Union[CookieJarNode, None] = None
        self.isVisited: bool = False

    def addCookie(self, newCookie: Cookie) -> None:
        for cookie in self.cookies:
            if cookie.name == newCookie.name:
                self.cookies.remove(cookie)
        self.cookies.append(newCookie)

    def addChild(self, childName: str):
        child = CookieJarNode(childName)
        self.children[child.name] = child
        child.parent = self
        return child

    def __repr__(self):
        return f"{self.name}"


class CookieJar:
    def __init__(self):
        self.root: CookieJarNode = CookieJarNode("root")

    def __traverse(self, domain: str, path: UrlPath, create: bool) -> Union[CookieJarNode, None]:
        currentNode: CookieJarNode = self.root
        if domain in currentNode.children:
            currentNode = currentNode.children[domain]
        else:
            if create:
                currentNode = currentNode.addChild(domain)
            else:
                return None
        for nodeName in path.pathList:
            if nodeName not in currentNode.children:
                if create:
                    currentNode = currentNode.addChild(nodeName)
                else:
                    return None
            else:
                currentNode = currentNode.children[nodeName]
        return currentNode

    def addRemoveCookie(self, cookie: Cookie) -> None:
        if cookie.value == "deleted" or cookie.isExpired():
            self.remove(cookie)
        else:
            self.__traverse(cookie.domain, UrlPath(cookie.getAttribute("path")), create=True).addCookie(cookie)

    def remove(self, toBeRemovedCookie: Cookie) -> None:
        node: CookieJarNode = self.__traverse(toBeRemovedCookie.domain, UrlPath(toBeRemovedCookie.getAttribute("path")),
                                              create=False)
        if node is not None:
            for cookie in node.cookies:
                if cookie.name == toBeRemovedCookie.name:
                    node.cookies.remove(cookie)
                    return
        raise TimeoutError(f"New cookie <{toBeRemovedCookie}> is expired or deleted")

    def visit(self, url: URL) -> None:
        self.__traverse(url.domain, UrlPath(url.path), create=True).isVisited = True

    def isVisited(self, url: URL) -> bool:
        node: CookieJarNode = self.__traverse(url.domain, UrlPath(url.path), create=False)
        if node is None:
            return False
        return node.isVisited

    def getCookies(self, url: URL) -> list[Cookie]:
        cookieList: list[Cookie] = list()
        currNode: CookieJarNode = self.root
        if url.domain in currNode.children:
            currNode = currNode.children[url.domain]
            cookieList.extend(currNode.cookies)
        else:
            return cookieList
        for nodeName in url.path.pathList:
            if nodeName in currNode.children:
                currNode = currNode.children[nodeName]
                cookieList.extend(currNode.cookies)
        return cookieList

    def getCookiesStr(self, url: URL) -> str:
        cookieList: list[Cookie] = self.getCookies(url)
        cookieStr: str = ""
        for cookie in cookieList:
            if not cookie.isExpired():
                cookieStr += f"{cookie}; "
            else:
                self.remove(cookie)
        cookieStr = cookieStr.strip()
        if cookieStr.endswith(";"):
            cookieStr = cookieStr[:-1]
        return cookieStr

    def __str__(self):
        pass

    def __contains__(self, item: Union[URL, Cookie]) -> bool:
        if isinstance(item, Cookie):
            url: URL = URL(f"{item.domain}{item.getAttribute('path')}")
        else:
            url: URL = item
        currNode: CookieJarNode = self.__traverse(url.domain, UrlPath(url.path), create=False)
        if isinstance(item, Cookie):
            return item in currNode.cookies
        else:
            return currNode is not None


class Response:
    def __init__(self, url: URL):
        self.url: URL = url
        self.responseString: str = ""
        self.httpVersion: str = ""
        self.statusCode: str = ""
        self.statusMessage: str = ""
        self.body: str = ""
        self.headers: dict[str, str] = dict()
        self.cookies: list[Cookie] = list()

    def rebuildResponse(self) -> str:
        responseString: str = f"{self.httpVersion} {self.statusCode} {self.statusMessage}\r\n"
        for headerName in self.headers:
            responseString += f"{headerName}: {self.headers[headerName]}\r\n"
        responseString += "\r\n"
        responseString += self.body
        return responseString

    def __str__(self):
        return f"{self.responseString}"


def parseResponse(responseString: str, url: URL) -> Response:
    response: Response = Response(url)
    responseString = sub(r"[\da-fA-F]{3,8}(\r\n|\n)", "", responseString)
    responseParts = responseString.split("\r\n\r\n")
    response.responseString = responseString
    responseHeadersLines: list[str] = responseParts[0].split("\r\n")
    statusList = responseHeadersLines[0].split(" ")
    response.httpVersion = statusList[0]
    response.statusCode = statusList[1]
    response.statusMessage = ' '.join(statusList[2:])
    for header in responseHeadersLines[1:]:
        headerName, headerValue = header.split(":", 1)
        headerValue = headerValue.strip()
        headerName = headerName.lower()
        if headerName == "set-cookie":
            currentCookie: Cookie = parseCookie(headerValue, url.domain)
            isAlreadyInList: bool = False
            for i, cookie in enumerate(response.cookies):
                if cookie.name == currentCookie.name and (cookie.value.lower() == "deleted" or cookie.isExpired()):
                    response.cookies[i] = currentCookie
                    isAlreadyInList = True
                    break
            if not isAlreadyInList:
                response.cookies.append(currentCookie)
        response.headers[headerName] = headerValue
    response.body = ''.join(responseParts[1:])
    return response


class Request:
    def __init__(self, requestType: str, requestURL: URL, content: str = None, cookiesStr: str = "",
                 moreHeaders: dict[str, str] = None, keepAlive: bool = True, acceptEnc: str = "utf-8",
                 referer: str = "",
                 options: bool = False):
        self.properties = {
            "requestType": requestType,
            "requestURL": requestURL,
            "content": content,
            "cookiesStr": cookiesStr,
            "moreHeaders": moreHeaders,
            "keepAlive": keepAlive,
            "Accept-Encoding": acceptEnc,
            "Referer": referer,
            "options": options
        }

    def __str__(self):
        requestStr: str = f"{self.properties['requestType']} {self.properties['requestURL']} HTTP/1.1\r\n"
        requestStr += f"Host: {self.properties['requestURL'].domain}\r\n"
        requestStr += f"Connection: {'keep-alive' if self.properties['keepAlive'] else 'close'}\r\n"
        if self.properties['Referer'] != "" and self.properties['Referer'] is not None:
            requestStr += f"Referer: {self.properties['referer']}\r\n"
        requestStr += "Pragma: no-cache\r\n" \
                      "Cache-Control: no-cache\r\n" \
                      "Upgrade-Insecure-Requests: 1\r\n"
        if self.properties['cookiesStr'] != "":
            requestStr += f"Cookie: {self.properties['cookiesStr']}\r\n"
        if self.properties['content'] is not None and self.properties['content'] != '':
            requestStr += f"Content-Length: {len(self.properties['content'])}\r\n"
        if self.properties['requestType'] == "POST" and (
                self.properties['content'] == '' or self.properties['content'] is None):
            requestStr += "Content-Length: 0\r\n"
        if self.properties['moreHeaders'] is not None:
            for header in self.properties['moreHeaders']:
                requestStr += f"{header}: {self.properties['moreHeaders'][header]}\r\n"
        requestStr += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                      "Chrome/101.0.4951.54 Safari/537.36\r\n" \
                      "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng" \
                      ",*/*;q=0.8,application/signed-exchange;v=b3;q=0.9\r\n"
        if self.properties['Accept-Encoding'] is not None and self.properties['Accept-Encoding'] != "":
            requestStr += f"Accept-Encoding: {self.properties['Accept-Encoding']}\r\n"
        if self.properties['options']:
            requestStr += 'sec-ch-ua: " Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"\r\n' \
                          'sec-ch-ua-mobile: ?0\r\n' \
                          'sec-ch-ua-platform: "Windows"\r\n' \
                          'sec-fetch-dest: document\r\n' \
                          'sec-fetch-mode: navigate\r\n' \
                          'sec-fetch-site: none\r\n' \
                          'sec-fetch-user: ?1\r\n' \
                          'sec-fetch-user: ?1\r\n'
        requestStr += "Accept-Language: en-GB,en;q=0.9\r\n" \
                      "\r\n"

        if self.properties["content"] is not None:
            requestStr += self.properties["content"]
        return requestStr

    def __setitem__(self, key, value):
        if key in self.properties:
            self.properties[key] = value
        else:
            raise KeyError(f"{key} is not a valid key")

    def __getitem__(self, item):
        return self.properties[item]


class Connection(object):
    def __init__(self, url: Union[str, URL], requestType: str, name: str, content: str = "",
                 headers: dict[str, str] = None):
        self.name: str = name
        if isinstance(url, str):
            self.url: URL = URL(url)
        else:
            self.url: URL = url
        self.requestType: str = requestType
        self.content: str = content
        self.headers: dict[str, str] = headers
        self.request: Request = None
        self.response: Response = None

    def __str__(self):
        return f"{self.name}"


# Returns the current time using the HTTP time format
#   (as explained in: https://httpwg.org/specs/rfc7231.html#http.date).
def getCurrHttpTime() -> str:
    return datetime.now().strftime("%a, %d-%b-%Y %H:%M:%S GMT")


def getLinksFromHTML(html: str, toFindRegex: str = toFindUrlRegex) -> [URL]:
    if html.startswith("file://"):
        htmlStrip = html.removeprefix("file://")
        with open(htmlStrip, 'r', encoding='ISO-8859-1') as f:
            content: str = f.read()
    else:
        content: str = html
    toTryURLs: [str] = findall(r"(" + toFindRegex + r")", content)
    URLs: list[URL] = []
    for tryUrl in toTryURLs:
        try:
            URLs.append(URL(tryUrl[0]))
        except Exception as e:
            print(e)  # TODO figure out how to handle this
            pass
    return URLs


def getUrlName(url: URL) -> str:
    name = f"{url.domain}_{'_'.join(url.path.pathList)}".replace("?", "_").strip(r"\:*?<>|")
    if len(name) > 100:
        name = name[:60]
    return name


def isFileUrl(url: URL) -> bool:
    commonMimeTypes: list[str] = [".aac", ".avif", ".avi", ".bmp", ".doc", ".docx", ".flv", ".gif", ".ico", ".jpeg",
                                  ".jpg", ".mid", ".midi", ".mp3", ".mp4", ".mpeg", ".mpg", ".oga", ".ogv", ".opus",
                                  ".otf", ".png", ".pdf", ".svg", ".swf", ".tif", ".tiff", ".ts", ".ttf", ".wav",
                                  ".weba", ".webm", "webp", ".woff", ".woff2", ".3gp", ".3g2", ".js"]
    for mimeType in commonMimeTypes:
        if mimeType in url.urlStr:
            return True
    return False
