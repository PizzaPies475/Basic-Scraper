import urllib.parse
import HttpConversation

# If the path is empty it will create a folder "HTTP-Logs".
# If the specified path doesn't exist, a new folder will be created in the relevant path.
logsFolderPath = "HTTP-Logs/"

# For logging invalid packets sent by the server.
# If the specified path doesn't exist, a new folder will be created in the relevant path.
invalidPacketsPath = "invalid_packets/"

# Has to be created separately.
# The file should be formatted as:
# 'username'\r\n
# 'ID'\r\n
# 'password'
credentialsPath = "config.txt"


def getCredentialsFromFile(credentialsFilePath: str) -> tuple[str, str, str]:
    with open(credentialsFilePath) as f:
        return f.readline().strip(), f.readline().strip(), f.readline().strip()


# This gets the SAML data given by the server when logging in to moodle.
# This relates to the transfer between the login server of the university and the moodle server.
# Without the info attached to the relevant request, the server won't recognize the client when logging in.
def getSamlInfo(requestName: str) -> str:
    with open(f"{logsFolderPath}{requestName}_content.html", 'r') as f:
        fileStr: str = ''.join(f.readlines())
        startSamlValue: int = fileStr.find("SAMLResponse") + 21
        endSamlValue: int = startSamlValue + fileStr[startSamlValue:].find('"')
        samlValue: str = urllib.parse.quote(fileStr[startSamlValue:endSamlValue], safe="")
        relayStateValue: str = urllib.parse.quote("https://moodle.tau.ac.il/auth/saml2/login.php", safe="")
        samlRequest = f"SAMLResponse={samlValue}&RelayState={relayStateValue}"
    return samlRequest


# When logging out the session key is needed to be sent to the server.
def getSessKey(requestName):
    with open(f"{logsFolderPath}{requestName}_content.html", 'r', encoding="ISO-8859-1") as f:
        for line in f:
            if "logout.php" in line:
                sessKey = line.strip().removeprefix('<a href="https://moodle.tau.ac.il/login/logout.php?sesskey=')
                sessKey = sessKey[:sessKey.find('"')]
                f.close()
                return sessKey


# Just for checking the cookies are valid.
def printUrlCookies(cookiesUrlDict):
    for host in cookiesUrlDict:
        print("host:", host, end='\r\n')
        for cookieName in cookiesUrlDict[host]:
            print(f"    {cookiesUrlDict[host][cookieName]}")
        print()


def findAllHomework(requestName):
    with open(f"{logsFolderPath}{requestName}_content.html", "r", encoding="ISO-8859-1") as f:
        identifier: str = "mod/assign"
        homeworkList: list[tuple] = []
        homeworkNum: int = 0
        linkEndLocation: int = 0
        for line in f:
            identifierIndex = line.find(identifier)
            while identifierIndex != -1:
                homeworkNum += 1
                linkStartLocation = linkEndLocation + identifierIndex - 25
                linkEndLocation = linkStartLocation + line[linkStartLocation:].find('"')
                homeworkLink = line[linkStartLocation:linkEndLocation]
                homeworkList.append((f"{requestName[4:]}HW{homeworkNum}", "GET", homeworkLink, None, None))
                identifierIndex = line[linkEndLocation:].find(identifier)
        return homeworkList


def main():
    with HttpConversation.HttpConversation(logsFolderPath) as conversation:
        # startURL = "https://moodle.tau.ac.il/"
        # clickLoginURL = "https://moodle.tau.ac.il/login/index.php"
        # continueLoginURL = "https://nidp.tau.ac.il/nidp/saml2/sso?id=10&sid=0&option=credential&sid=0"
        # connectionList = [("goToMoodle", "GET", startURL, None, None),
        #                   ("clickLogin", "GET", clickLoginURL, None, None),
        #                   ("continueClickLogin", "POST", continueLoginURL, None, None)]
        # conversation.startConversation(connectionList)
        # sendFormURL = "https://nidp.tau.ac.il/nidp/saml2/sso?sid=0&sid=0&uiDestination=contentDiv"
        # credentials = getCredentialsFromFile(credentialsPath)
        # moodleCredentials = f"option=credential&Ecom_User_ID={credentials[0]}&Ecom_User_Pid={credentials[1]}&Ecom_Password={credentials[2]}"
        # headersDict = {"X-Requested-With": "XMLHttpRequest",
        #                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        # connectionList = [("sendForm", "POST", sendFormURL, moodleCredentials, headersDict),
        #                   ("continueSendForm", "GET", "https://nidp.tau.ac.il/nidp/saml2/sso?sid=0", None, None)]
        # conversation.startConversation(connectionList)
        # samlInfo = getSamlInfo(
        #     f"{conversation.getIndex() - 1}continueSendFormGET")  # Go to last request and get the SAML info.
        # headersDict = {"Content-Type": "application/x-www-form-urlencoded"}
        # connectionList = [("goToMoodleSaml", "POST",
        #                    "https://moodle.tau.ac.il/auth/saml2/sp/saml2-acs.php/moodle.tau.ac.il", samlInfo,
        #                    headersDict)]
        # conversation.startConversation(connectionList)
        # headersDict = {"Sec-Fetch-Site": "same-origin",
        #                "Sec-Fetch-Mode": "navigate",
        #                "Sec-Fetch-User": "?1",
        #                "Sec-Fetch-Dest": "document",
        #                "Referer": "https://moodle.tau.ac.il/my/",
        #                "sec-ch-ua": '" Not A;Brand";v = "99", "Chromium";v = "98", "Google Chrome";v = "98"',
        #                "sec-ch-ua-mobile": '?0',
        #                "sec-ch-ua-platform": '"Windows"'}
        # connectionList = [
        #     # ("goToTochna", "GET", "https://moodle.tau.ac.il/course/view.php?id=368215799", None, None)]
        #     # ('goToMavnat', 'GET', 'https://moodle.tau.ac.il/course/view.php?id=368215899', None, headersDict),
        #     # ('goToMadar', 'GET', 'https://moodle.tau.ac.il/course/view.php?id=509174512', None, headersDict),
        #     ("goToHedva", "GET", "https://moodle.tau.ac.il/course/view.php?id=509174701", None, headersDict),
        #     # ('goToStat', 'GET', 'https://moodle.tau.ac.il/course/view.php?id=509280199', None, headersDict),
        #     # ('goToMalas', 'GET', 'https://moodle.tau.ac.il/course/view.php?id=512356101', None, headersDict)
        # ]
        # conversation.startConversation(connectionList)
        # sessKey = getSessKey("9goToMoodleSaml1GET")
        # hwConnectionList: list[tuple] = findAllHomework("10goToHedvaGET")
        # #conversation.startConversation(hwConnectionList)
        # connectionList = [("logout", "GET", f"https://moodle.tau.ac.il/login/logout.php?sesskey={sessKey}", None, None)]
        # conversation.startConversation(connectionList)
        # conversation.printAllConnections()
        conversation.showInChrome(input("Enter request name to show in Chrome: "))


if __name__ == '__main__':
    main()
