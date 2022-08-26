import httpUtils
import re

testFilesLocation = "test_files/"
referencePathDict = {"": [], "/": [], "/index.html": ["index.html"], "/index.html/": ["index.html"],
                     "/index.html/index.html": ["index.html", "index.html"],
                     "/index.html/index.html/": ["index.html", "index.html"],
                     "//a/": ["", "a"], "//a/b/": ["", "a", "b"], "//a/b/c/": ["", "a", "b", "c"],
                     "/a///": ["a", "", ""], "///": ["", ""]}
# The dictionary is built like: {url: [fullUrl, scheme, domain, port, path, fragment]}
referenceUrlDict = {"http://www.google.com": ["http://www.google.com", "http", "www.google.com", "", [], ""],
                    "http://www.google.com/": ["http://www.google.com/", "http", "www.google.com", "", [], ""],
                    "http://www.google.com/index.html": ["http://www.google.com/index.html", "http",
                                                         "www.google.com", "", ["index.html"], ""],
                    "http://www.google.com/index.html#fragment": ["http://www.google.com/index.html#fragment",
                                                                  "http", "www.google.com", "", ["index.html"],
                                                                  "fragment"],
                    "https://www.example.com:443/index.html": ["https://www.example.com:443/index.html", "https",
                                                               "www.example.com", "443", ["index.html"], ""],
                    "https://www.example.com:443/index.html#fragment": [
                        "https://www.example.com:443/index.html#fragment", "https", "www.example.com", "443",
                        ["index.html"], "fragment"],
                    "ftp://aaa.1f1fas2.co.il:80/sadlkpm223klfmkdw;mMKLmklsa;l&/iasd.kd#fragment": [
                        "ftp://aaa.1f1fas2.co.il:80/sadlkpm223klfmkdw;mMKLmklsa;l&/iasd.kd#fragment", "ftp",
                        "aaa.1f1fas2.co.il", "80", ["sadlkpm223klfmkdw;mMKLmklsa;l&", "iasd.kd"], "fragment"]}


def test_isValidUrlRegex():
    with open(f"{testFilesLocation}test_URLs.txt", "r") as f:
        for line in f:
            line = line.strip()
            assert bool(re.match(httpUtils.validUrlRegex, line))


def test_isValidCookieRegex():
    with open(f"{testFilesLocation}test_cookies.txt", "r") as f:
        for line in f:
            line = line.strip()
            assert bool(re.match(httpUtils.validCookieRegex, line))


def test_parsePath():
    for path in referencePathDict:
        assert referencePathDict[path] == httpUtils.parsePath(path).pathList


def test_URL():
    def urlToList(url: httpUtils.URL):
        return [url.urlStr, url.scheme, url.domain, url.port, url.path.pathList, url.fragment]

    for urlItem in referenceUrlDict:
        assert referenceUrlDict[urlItem] == urlToList(httpUtils.URL(urlItem))


def test_parseCookie():
    with open(f"{testFilesLocation}test_cookies.txt", "r") as f:
        for line in f:
            line = line.strip()
            cookie: httpUtils.Cookie = httpUtils.parseCookie(line, "")
            assert str(cookie) in line


def test_getLinksFromHTML():
    testLinks: list[httpUtils.URL] = httpUtils.getLinksFromHTML(f"file://{testFilesLocation}test_orefPage.txt")
    referenceLinks: list[httpUtils.URL] = []
    with open(f"{testFilesLocation}test_orefPageUrls.txt", "r") as f:
        for line in f:
            line = line.strip()
            referenceLinks.append(httpUtils.URL(line))
    assert set(referenceLinks) == set(testLinks)


# CookieJar tests
def test_addRemoveCookie():
    cookiesList: list[httpUtils.Cookie] = []
    with open(f"{testFilesLocation}test_cookies.txt", "r") as f:
        for line in f:
            line = line.strip()
            cookiesList.append(httpUtils.parseCookie(line, "www.example.com"))
    cookieJar: httpUtils.CookieJar = httpUtils.CookieJar()
    for cookie in cookiesList:
        cookieJar.addRemoveCookie(cookie)
        if cookie.value != "deleted" and not cookie.isExpired():
            assert cookie in cookieJar
    for i, cookie in enumerate(cookiesList):
        if cookie.name == "ADRUM_BT" and cookie.value != "deleted":
            adrumCookie = cookie
        elif cookie.value != "deleted" and not cookie.isExpired():
            assert cookie in cookieJar
    assert adrumCookie not in cookieJar


def test_visit():
    urlList = referenceUrlDict.keys()
    cookieJar = httpUtils.CookieJar()
    for url in urlList:
        cookieJar.visit(httpUtils.URL(url))


def test_getCookies():
    assert True


def test_request():

    def assertions(requestToTest: httpUtils.Request,  requestToCompare: httpUtils.Request = None):
        if requestToCompare is not None:
            assert requestToTest.type == requestToCompare.type
            assert requestToTest.url == requestToCompare.url
            assert requestToTest.headers == requestToCompare.headers
            assert requestToTest.content == requestToCompare.content
        assert requestToTest.type == "GET"
        assert requestToTest.url == httpUtils.URL("https://moodle.tau.ac.il/")
        assert requestToTest.content == "requestContentTest"
        assert requestToTest.headers["Accept"] == "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        assert requestToTest.headers["Accept-Encoding"] == "gzip, deflate, br"
        assert requestToTest.headers["Accept-Language"] == "en-GB,en;q=0.9"
        assert requestToTest.headers["Cache-Control"] == "no-cache"
        assert requestToTest.headers["Connection"] == "keep-alive"
        assert requestToTest.headers["Host"] == "moodle.tau.ac.il"
        assert requestToTest.headers["Pragma"] == "no-cache"
        assert requestToTest.headers["Sec-Fetch-Dest"] == "document"
        assert requestToTest.headers["Sec-Fetch-Mode"] == "navigate"
        assert requestToTest.headers["Sec-Fetch-Site"] == "none"
        assert requestToTest.headers["Sec-Fetch-User"] == "?1"
        assert requestToTest.headers["Upgrade-Insecure-Requests"] == "1"
        assert requestToTest.headers["User-Agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        assert requestToTest.headers["Sec-Ch-Ua"] == '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"'
        assert requestToTest.headers["Sec-Ch-Ua-Mobile"] == "?0"
        assert requestToTest.headers["Sec-Ch-Ua-Platform"] == '"Windows"'

    with open(f"{testFilesLocation}test_request.txt", "r") as f:
        requestStr = f.read()
    request = httpUtils.parseRequest(requestStr)
    assertions(request)
    request = httpUtils.Request("GET", httpUtils.URL("https://moodle.tau.ac.il/"), True, "requestContentTest", acceptEnc="gzip, deflate, br", shouldOptionalHeaders=True)
    request["Sec-Fetch-Mode"] = "navigate"
    request["Sec-Fetch-Site"] = "none"
    assertions(request)
