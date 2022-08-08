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
