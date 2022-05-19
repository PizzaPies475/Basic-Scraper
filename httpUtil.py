from datetime import datetime
import generalUtils
from re import match, findall
from Cookie import Cookie


# Returns the current time using the HTTP time format
#   (as explained in: https://httpwg.org/specs/rfc7231.html#http.date).
def getCurrHttpTime() -> str:
    dayOfWeekList: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_name = dayOfWeekList[datetime.today().weekday()]
    return datetime.now().strftime(day_name + ", %d-%b-%Y %H:%M:%S GMT")


def getLinksFromHTML(html: str) -> list[str]:
    if html.startswith("file://"):
        htmlStrip = html.removeprefix("file://")
        with open(htmlStrip, 'r', encoding='ISO-8859-1') as f:
            content: str = f.read()
    else:
        content: str = html
    URLs: list[str] = findall(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.["
                              r"a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))["
                              r"a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})", content)
    linkList: list[str] = []
    for url in URLs:
        url = url.strip("'")
        if '"' in url:
            linkList.append(url.split('"')[0])
        else:
            linkList.append(url)
    return linkList


# This function builds a VERY basic request.
# It was only checked with a small amount of servers.
# With more advanced servers (Google, Facebook, etc.) the request might be invalid, and not work.
# It will take the relevant cookies from the urlCookiesDict and shove them to the request,
#   along with any more headers given.
# NOTE: The function won't check if the cookies are correct and assumes all the cookies in the dictionary are valid and
#   assembled correctly.
# The default encoding requested is utf-8.
def buildRequest(requestType: str, requestURL: str, content: str = None, urlCookiesDict: dict = None,
                 moreHeaders: dict = None, keepAlive: bool = True, acceptEnc: str = "utf-8", referer: str = "",
                 options: bool = False) -> str:
    request: str = f"{requestType} {requestURL} HTTP/1.1\r\n"
    request += f"Host: {getDomainFromUrl(requestURL)}\r\n"
    request += f"Connection: {'keep-alive' if keepAlive else 'close'}\r\n"
    if referer != "" and referer is not None:
        request += f"Referer: {referer}\r\n"
    request += "Pragma: no-cache\r\n" \
               "Cache-Control: no-cache\r\n" \
               "Upgrade-Insecure-Requests: 1\r\n"
    if urlCookiesDict is not None and getDomainFromUrl(requestURL) in urlCookiesDict:
        request += cookiesDictToStr(urlCookiesDict[getDomainFromUrl(requestURL)], requestURL)
    if content is not None and content != '':
        request += f"Content-Length: {len(content)}\r\n"
    if requestType == "POST" and (content == '' or content is None):
        request += "Content-Length: 0\r\n"
    if moreHeaders is not None:
        for header in moreHeaders:
            request += f"{header}: {moreHeaders[header]}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
               "Chrome/101.0.4951.54 Safari/537.36\r\n" \
               "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;" \
               "q=0.8,application/signed-exchange;v=b3;q=0.9\r\n"
    if acceptEnc is not None and acceptEnc != "":
        request += f"Accept-Encoding: {acceptEnc}\r\n"
    if options:
        request += 'sec-ch-ua: " Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"\r\n' \
                   'sec-ch-ua-mobile: ?0\r\n' \
                   'sec-ch-ua-platform: "Windows"\r\n' \
                   'sec-fetch-dest: document\r\n' \
                   'sec-fetch-mode: navigate\r\n' \
                   'sec-fetch-site: none\r\n' \
                   'sec-fetch-user: ?1\r\n' \
                   'sec-fetch-user: ?1\r\n'
    request += "Accept-Language: en-GB,en;q=0.9\r\n" \
               "\r\n"

    if content is not None:
        request += content
    return request


# Used by buildRequest to convert the dictionary of a given URL into a string to be added to the request.
def cookiesDictToStr(cookiesDict: dict[str: Cookie], currURL: str) -> str:
    cookiesStr: str = ""
    if cookiesDict:
        cookiesStr += "Cookie: "
        for cookieName in cookiesDict:
            if checkUrlToPath(currURL, cookiesDict[cookieName].getAttribute("path")):
                cookiesStr += f"{cookiesDict[cookieName]};"
        cookiesStr = cookiesStr[:-2] + "\r\n"
    return cookiesStr


def getDomainFromUrl(url: str) -> str:
    urlNoHttps: str = url.removeprefix("https://")
    urlNoHttps = urlNoHttps.removeprefix("http://")
    if '/' in urlNoHttps:
        return urlNoHttps.split("/")[0]
    return urlNoHttps


def getPathFromUrl(url: str) -> str:
    urlNoHttps: str = url.removeprefix("https://")
    urlNoHttps = urlNoHttps.removeprefix("http://")
    if urlNoHttps.find(".") == -1:
        return urlNoHttps
    if urlNoHttps.find("/") == -1:
        return "/"
    return urlNoHttps[urlNoHttps.find('/'):]


def logData(data, fileName: str, log: bool = True):
    if log:
        if type(data) is bytes:
            generalUtils.clearFileAndWrite(fileName, 'wb', data)
        elif type(data) is str:
            generalUtils.clearFileAndWrite(fileName, 'w', data)
        else:
            raise TypeError("Data must be bytes or str")


def isValidURL(url: str) -> bool:
    return bool(match(r"[-a-zA-Z0-9@:%.\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%\+.~#?&//=]*)", url)) or \
           bool(match(
               r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%.\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%\+.~#?&//=]*)",
               url))


def checkUrlToPath(URL: str, pathToCheck: str) -> bool:
    UrlPath: str = getPathFromUrl(URL)
    if UrlPath == pathToCheck:
        return True
    pathToCheck = pathToCheck.removeprefix("/")
    pathToCheck = pathToCheck.removesuffix("/")
    pathToCheck = f"/{pathToCheck}/"
    if pathToCheck == "//":
        pathToCheck = "/"
    UrlPath = UrlPath.removeprefix("/")
    UrlPath = UrlPath.removesuffix("/")
    UrlPath = f"/{UrlPath}/"
    if UrlPath == "//":
        UrlPath = "/"
    if UrlPath.startswith(pathToCheck):
        return True
    return False


# Just for checking the cookies are valid.
def printAllCookies(cookiesUrlDict: dict[str: Cookie]) -> None:
    for host in cookiesUrlDict:
        print("host:", host, end='\r\n')
        for cookieName in cookiesUrlDict[host]:
            print(f"    {cookiesUrlDict[host][cookieName]}  ", end="")
            for attribute in cookiesUrlDict[host][cookieName].getAttributes():
                print(f"{attribute}={cookiesUrlDict[host][cookieName].getAttribute(attribute)}  ")
            print()
        print()


def isSameOrigin(url1: str, url2: str) -> bool:
    url1Domain: str = getDomainFromUrl(url1)
    url2Domain: str = getDomainFromUrl(url2)
    return url1Domain == url2Domain


def getDomainName(url: str) -> str:  # TODO Return more significant domain name
    return url.removeprefix("https://").removeprefix("http://").replace('?', ''). \
        replace('/', '_').replace(':', '').replace("\/", '')[:40]


def isFileUrl(url: str) -> bool:
    commonMimeTypes: list[str] = [".aac", ".avif", ".avi", ".bmp", ".doc", ".docx", ".flv", ".gif", ".ico", ".jpeg",
                                  ".jpg", ".mid", ".midi", ".mp3", ".mp4", ".mpeg", ".mpg", ".oga", ".ogv", ".opus",
                                  ".otf", ".png", ".pdf", ".svg", ".swf", ".tif", ".tiff", ".ts", ".ttf", ".wav",
                                  ".weba", ".webm", "webp", ".woff", ".woff2", ".3gp", ".3g2", ".js"]
    for mimeType in commonMimeTypes:
        if mimeType in url:
            return True
    return False
