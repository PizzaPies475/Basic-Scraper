import httpUtils
import unittest
import re

testFilesLocation = "test_files/"

class TestHttpConversation(unittest.TestCase):

    def test_isValidUrlRegex(self):
        with open(f"{testFilesLocation}test_URLs.txt", "r") as f:
            for line in f:
                line = line.strip()
                with self.subTest(URL=line):
                    self.assertTrue(bool(re.match(httpUtils.validUrlRegex, line)))

    def test_isValidCookieRegex(self):
        with open(f"{testFilesLocation}test_cookies.txt", "r") as f:
            for line in f:
                line = line.strip()
                with self.subTest(cookie=line):
                    self.assertTrue(bool(re.match(httpUtils.validCookieRegex, line)))

    def test_parseCookie(self):
        with open(f"{testFilesLocation}test_cookies.txt", "r") as f:
            for line in f:
                line = line.strip()
                with self.subTest(cookie=line):
                    cookie: httpUtils.Cookie = httpUtils.parseCookie(line, "")
                    self.assertTrue(str(cookie) in line)

    def test_getLinksFromHTML(self):
        testLinks: list[httpUtils.URL] = httpUtils.getLinksFromHTML(f"file://{testFilesLocation}test_orefPage.txt")
        referenceLinks: list[httpUtils.URL] = []
        with open(f"{testFilesLocation}test_orefPageUrls.txt", "r") as f:
            for line in f:
                line = line.strip()
                referenceLinks.append(httpUtils.URL(line))
        self.assertEqual(set(referenceLinks), set(testLinks))

    def test_parsePath(self):
        pass



if __name__ == "__main__":
    unittest.main()
