from datetime import datetime, timedelta
from re import match, findall, sub
from typing import Union

dayOfWeekList: [str] = ["Mon", "Tue", "Wed", "Thu", "Fri", 'Sat', 'Sun']
validUrlRegex = r"((http(s)?:\/\/)?[\w-]+(\.[\w-]+)+(\/[\w\/?=&%+\.]+)*/?)"


class WrongProtocolException(ValueError):
    pass


class UrlPath:

    def __init__(self, pathStr: str):
        # if not match("^(\/([\w\.-]+))*\/?$", pathStr):  # "/" or "/path/to/file" or "/path/to/file/"
        #     raise ValueError(f"Invalid path: {pathStr}")
        if pathStr.startswith("/"):
            pathStr = pathStr[1:]
        self.pathList: [str] = pathStr.split("/")
        pass

    def __str__(self):
        return f"/{'/'.join(self.pathList)}"

    def __len__(self):
        return len(self.pathList)


class URL:
    def __init__(self, urlStr: str):
        if not isValidURL(urlStr):
            raise ValueError(f"Invalid URL: {urlStr}")

        self.urlStr: str = urlStr
        self.protocol: str = getProtocolFromUrl(urlStr)
        self.domain: str = getDomainFromUrl(urlStr)
        self.path: UrlPath = getPathFromUrl(urlStr)
        self.fragment: str = getFragmentFromUrl(urlStr)

    def __str__(self):
        return f"https://{self.domain}{self.path}"

    def __repr__(self):
        return f"https://{self.domain}{self.path}"


def isValidURL(urlStr: str) -> bool:
    try:
        return bool(match(r"^" + validUrlRegex + r"$", urlStr))
    except Exception as e:
        print(e)
        return False


def getProtocolFromUrl(urlStr: str) -> str:
    if "://" in urlStr:
        return urlStr.split("://")[0]
    return ""


def getDomainFromUrl(urlStr: str) -> str:
    urlNoHttps: str = urlStr.removeprefix("https://")
    urlNoHttps = urlNoHttps.removeprefix("http://")
    if '/' in urlNoHttps:
        return urlNoHttps.split("/")[0]
    return urlNoHttps


def getPathFromUrl(urlStr: str) -> UrlPath:
    urlNoHttps: str = urlStr.removeprefix("https://")
    urlNoHttps = urlNoHttps.removeprefix("http://")
    if '/' in urlNoHttps:
        pathStr: str = f"/{'/'.join(urlNoHttps.split('/')[1:])}"
    else:
        pathStr: str = "/"
    return UrlPath(pathStr)


def getFragmentFromUrl(urlStr: str) -> str:
    if '#' in urlStr:
        return urlStr.split('#')[1]
    return ""


def getQueriesFromUrl(urlStr: str) -> [str]:
    return findall(r"\?([^\s\/?]*)", urlStr)


def checkUrlToPath(url: URL, path: [str]) -> bool:
    urlPath = url.path.pathList
    if len(urlPath) > len(path):
        for i in range(len(path)):
            if urlPath[i] != path[i]:
                return False
        return True
    return False


class Cookie:
    def __init__(self, cookieName: str, domain: str, cookieValue: str = None, cookieAttributes: dict[str: str] = None):
        try:
            if cookieValue is not None:
                self.domain: str = domain
                self.name: str = cookieName
                self.value: str = cookieValue
                self.attributes: dict[str: str] = cookieAttributes
            else:
                cookieList: [str] = cookieName.split()
                self.domain: str = domain
                self.name: str = cookieList[0].split('=')[0]
                self.value: str = cookieList[0].split('=')[1].removesuffix(';')
                self.attributes: dict[str: str] = dict()
                i: int = 1
                maxAgeFlag = False
                while i in range(1, len(cookieList)):
                    if "Max-Age" in cookieList[i] or "max-age" in cookieList[i]:
                        day_name: str = dayOfWeekList[datetime.today().weekday()]
                        maxAgeValue: int = int(cookieList[i][8:-1])
                        maxAgeDays: int = maxAgeValue // (24 * 60 * 60)
                        maxAgeHours: int = (maxAgeValue - maxAgeDays * (24 * 60 * 60)) // 360
                        maxAgeMinutes: int = (maxAgeValue - maxAgeHours * 360 - maxAgeDays * (24 * 60 * 60)) // 60
                        maxAgeSeconds: int = (maxAgeValue - maxAgeHours * 360 - maxAgeMinutes * 60) % 60
                        maxAgeTime: str = f"{str(maxAgeHours).rjust(2, '0')}:{str(maxAgeMinutes).rjust(2, '0')}:" \
                                          f"{str(maxAgeSeconds).rjust(2, '0')}"
                        maxAgeToAdd: datetime = datetime.strptime(maxAgeTime, "%H:%M:%S")
                        maxAgeDate: datetime = datetime.now() + timedelta(days=maxAgeDays, hours=maxAgeToAdd.hour,
                                                                          minutes=maxAgeToAdd.minute,
                                                                          seconds=maxAgeToAdd.second)
                        self.attributes["expires"] = maxAgeDate.strftime(day_name + ", %d-%b-%Y %H:%M:%S GMT")
                        i += 2
                        maxAgeFlag: bool = True
                    elif maxAgeFlag and "expires" in cookieList[i]:
                        i += 4
                    elif "expires" in cookieList[i] or "Expires" in cookieList[i]:
                        self.attributes[
                            'expires'] = f"{cookieList[i][8:]} {cookieList[i + 1]} {cookieList[i + 2]} " \
                                         f"{cookieList[i + 3][:-1]} "
                        i += 4
                    elif '=' in cookieList[i]:
                        self.attributes[cookieList[i].split('=')[0]] = cookieList[i].split('=')[1].removesuffix(';')
                        i += 1
                    else:
                        self.attributes[cookieList[i].removesuffix(';')] = True
                        i += 1
                if "path" not in self.attributes and "Path" not in self.attributes:
                    self.attributes["path"] = '/'
                if "Path" in self.attributes:
                    self.attributes["path"] = self.attributes["Path"]
                    del self.attributes["Path"]
                self.attributes["path"]: UrlPath = UrlPath(self.attributes["path"])

        except Exception as e:
            print("Failed to create cookie:", cookieName)
            raise e

    def getAttribute(self, attribute: str):
        if attribute in self.attributes:
            return self.attributes[attribute]

    # Returns True if the current time is later than the 'expires' attribute value
    #   (which is formatted as HTTP time, see getCurrHttpTime comment in httpUtil) of the given cookie.
    # If the cookie doesn't have an 'expires' attribute, the function returns False (duh).
    def isExpired(self) -> bool:
        if self.getAttribute("expires"):
            return datetime.strptime(self.getAttribute("expires")[5:].strip(), "%d-%b-%Y %H:%M:%S GMT") < datetime.now()
        else:
            return False

    def __str__(self):
        return f"{self.name}={self.value}"

    def __repr__(self):
        return f"{self.name}={self.value}"


class CookieJar:
    def __init__(self):
        self.cookies: dict[str: dict] = dict()
        self.cookiesList: [Cookie] = list()

    def addCookie(self, cookie: Cookie):
        self.cookiesList.append(cookie)
        domain: str = cookie.domain
        if domain not in self.cookies:
            self.cookies[domain] = {"cookies": list()}
        currDict: dict = self.cookies[domain]
        pathList: list[str] = cookie.getAttribute("path").pathList
        for path in pathList:
            if path in currDict:
                currDict = currDict[path]
            else:
                currDict[path] = dict()
                currDict = currDict[path]
                currDict["cookies"]: list[Cookie] = []
        currDict["cookies"].append(cookie)

    def addPath(self, url: URL) -> None:
        domain: str = url.domain
        pathList: list[str] = url.path.pathList
        if domain not in self.cookies:
            self.cookies[domain] = dict()
            self.cookies[domain]["cookies"]: list[Cookie] = list()
        currDict: dict = self.cookies[domain]
        for pathPart in pathList:
            if pathPart in currDict:
                currDict = currDict[pathPart]
            else:
                currDict[pathPart] = dict()
                currDict = currDict[pathPart]
                currDict["cookies"]: list[Cookie] = []

    def getCookies(self, url: URL) -> list[Cookie]:
        cookieList: list[Cookie] = list()
        domain = url.domain
        if domain in self.cookies:
            currDict: dict = self.cookies[url.domain]
            pathList: list[str] = url.path.pathList
            if currDict["cookies"]:
                cookieList.extend(currDict["cookies"])
            for path in pathList:
                if path in currDict:
                    currDict = currDict[path]
                if currDict["cookies"]:
                    cookieList.extend(currDict["cookies"])
                else:
                    return cookieList
        return cookieList

    def getCookiesStr(self, url: URL) -> str:
        cookieList: list[Cookie] = self.getCookies(url)
        cookieStr: str = ""
        for cookie in cookieList:
            if not cookie.isExpired() or cookie.value.lower() == "deleted":
                cookieStr += f"{cookie};"
            else:
                self.remove(cookie)
        if cookieStr.endswith(";"):
            cookieStr = cookieStr[:-1]
        return cookieStr

    def remove(self, cookie: Cookie) -> None:
        currDict: dict = self.cookies[cookie.getAttribute("domain")]
        pathList: list[str] = cookie.getAttribute("path").pathList
        for pathPart in pathList:
            if pathPart in currDict:
                currDict = currDict[pathPart]
            else:
                raise ValueError("Cookie not found")
        currDict["cookies"].remove(cookie)

    def getTreePathString(self) -> str:
        treePathString: str = ""
        for domain in self.cookies:
            treePathString += f"{domain}:\n"
            currDict: dict = self.cookies[domain]
            for path in currDict:
                if path == "cookies":
                    continue
                treePathString += f"\t{path}:\n"
                currDict = currDict[path]
                for cookie in currDict["cookies"]:
                    treePathString += f"\t\t{cookie}\n"
        return treePathString

    def __contains__(self, url: URL) -> bool:
        if url.domain in self.cookies:
            currDict: dict = self.cookies[url.domain]
        else:
            return False
        path: UrlPath = url.path
        for pathPart in path.pathList:
            if pathPart in currDict:
                currDict = currDict[pathPart]
            else:
                return False
        return True

    def __str__(self):
        return str(self.cookies)


class Response:
    def __init__(self, url: URL):
        self.url: URL = url
        self.responseString = ""
        self.httpVersion: str = ""
        self.statusCode: str = ""
        self.statusMessage: str = ""
        self.body: str = ""
        self.headers: dict[str: str] = dict()
        self.cookies: list[Cookie] = list()

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
        if "set-cookie" in headerName:
            response.cookies.append(Cookie(headerValue, url.domain))
        response.headers[headerName] = headerValue
    response.body = ''.join(responseParts[1:])
    return response


class Request:
    def __init__(self, requestType: str, requestURL: URL, content: str = None, cookiesStr: str = "",
                 moreHeaders: dict[str: str] = None, keepAlive: bool = True, acceptEnc: str = "utf-8",
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
                 headers: dict[str:str] = None, keepAlive: bool = True):
        self.name: str = name
        if isinstance(url, str):
            self.url: URL = URL(url)
        self.url: URL = url
        self.requestType: str = requestType
        self.content: str = content
        self.headers: dict[str, str] = headers
        self.keepAlive: bool = keepAlive
        self.request: Request = None
        self.response: Response = None

    def __str__(self):
        return f"{self.name}"


# Returns the current time using the HTTP time format
#   (as explained in: https://httpwg.org/specs/rfc7231.html#http.date).
def getCurrHttpTime() -> str:
    day_name = dayOfWeekList[datetime.today().weekday()]
    return datetime.now().strftime(day_name + ", %d-%b-%Y %H:%M:%S GMT")


def getLinksFromHTML(html: str) -> [URL]:
    if html.startswith("file://"):
        htmlStrip = html.removeprefix("file://")
        with open(htmlStrip, 'r', encoding='ISO-8859-1') as f:
            content: str = f.read()
    else:
        content: str = html
    URLs: [str] = findall(validUrlRegex, content)
    for i in range(len(URLs)):
        URLs[i] = URL(URLs[i][0])
    return URLs


def getUrlName(url: URL) -> str:
    name = f"{url.domain}_{'_'.join(url.path.pathList)}".replace("?", "_").strip(r"\:*?<>|")
    if len(name) > 100:
        name = name[:100]
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
