from datetime import datetime


# Returns the current time using the HTTP time format
#   (as explained in: https://httpwg.org/specs/rfc7231.html#http.date).
def getCurrHttpTime() -> str:
    dayOfWeekList: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_name = dayOfWeekList[datetime.today().weekday()]
    return datetime.now().strftime(day_name + ", %d-%b-%Y %H:%M:%S GMT")


# This function builds a VERY basic request.
# It was only checked with a small amount of servers.
# With more advanced servers (Google, Facebook, etc.) the request might be invalid, and not work.
# It will take the relevant cookies from the urlCookiesDict and shove them to the request,
#   along with any more headers given.
# NOTE: The function won't check if the cookies are valid (like if they are not expired) and assumes all the
#   cookies in the dictionary are valid and assembled correctly.
# The default encoding requested is utf-8.
def buildRequest(requestType: str, requestURL: str, content: str = None, urlCookiesDict: dict = None,
                 moreHeaders: dict = None, keepAlive=True, acceptEnc: str = "utf-8") -> str:
    request: str = f"{requestType} {requestURL} HTTP/1.1\r\n"
    request += f"Host: {getDomainFromUrl(requestURL)}\r\n"
    request += f"Connection: {'keep-alive' if keepAlive else 'close'}\r\n"
    request += "Pragma: no-cache\r\n" \
               "Cache-Control: no-cache\r\n" \
               "Upgrade-Insecure-Requests: 1\r\n"
    if urlCookiesDict is not None and getDomainFromUrl(requestURL) in urlCookiesDict:
        request += cookiesDictToStr(urlCookiesDict[getDomainFromUrl(requestURL)])
    if content is not None and content != '':
        request += f"Content-Length: {len(content)}\r\n"
    if moreHeaders is not None:
        for header in moreHeaders:
            request += f"{header}: {moreHeaders[header]}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
               "Chrome/98.0.4758.81 Safari/537.36\r\n" \
               "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;" \
               "q=0.8,application/signed-exchange;v=b3;q=0.9\r\n"
    request += f"Accept-Encoding: {acceptEnc}\r\n"
    request += "Accept-Language: en-GB,en;q=0.9\r\n" \
               "\r\n"
    if content is not None:
        request += content
    return request


# Used by buildRequest to convert the dictionary of a given URL into a string to be added to the request.
def cookiesDictToStr(cookiesDict: dict) -> str:
    cookiesStr: str = ""
    if cookiesDict:
        cookiesStr += "Cookie: "
        for cookieName in cookiesDict:
            cookiesStr += str(cookiesDict[cookieName]) + "; "
        cookiesStr = cookiesStr[:-2] + "\r\n"
    return cookiesStr


def getDomainFromUrl(url: str) -> str:
    urlNoHttps = url.removeprefix("https://")
    return urlNoHttps[:urlNoHttps.find('/')]


def isValidResponse(data: bytes) -> bool:
    return len(data) > 14 and "HTTP/1.1".encode() in data and int(data.decode(encoding="ISO-8859-1")[9:12]) in \
           range(100, 600)
