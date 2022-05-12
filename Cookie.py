from datetime import datetime, timedelta

dayOfWeekList: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", 'Sat', 'Sun']


class Cookie:

    def __init__(self, cookieName: str, domain: str, cookieValue: str = None, cookieAttributes: dict[str: str] = None):
        try:
            if cookieValue is not None:
                self.domain: str = domain
                self.name: str = cookieName
                self.value: str = cookieValue
                self.attributes: dict[str: str] = cookieAttributes
            else:
                cookieList: list[str] = cookieName.split()
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
                        maxAgeTime: str = f"{str(maxAgeHours).rjust(2, '0')}:{str(maxAgeMinutes).rjust(2, '0')}:{str(maxAgeSeconds).rjust(2, '0')}"
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
                            'expires'] = f"{cookieList[i][8:]} {cookieList[i + 1]} {cookieList[i + 2]} {cookieList[i + 3][:-1]} "
                        i += 4
                    elif '=' in cookieList[i]:
                        self.attributes[cookieList[i].split('=')[0]] = cookieList[i].split('=')[1].removesuffix(';')
                        i += 1
                    else:
                        self.attributes[cookieList[i].removesuffix(';')] = True
                        i += 1
                if "path" not in self.attributes and "Path" not in self.attributes:  # TODO Learn about path and correct as needed.
                    self.attributes["path"] = '/'
                if "Path" in self.attributes:
                    self.attributes["path"] = self.attributes["Path"]
                    del self.attributes["Path"]
        except Exception as e:
            print("Failed to create cookie:", cookieName)
            raise e

    def getName(self) -> str:
        return self.name

    def getValue(self) -> str:
        return self.value

    def getAttributes(self) -> dict:
        return self.attributes

    def getAttribute(self, attribute: str) -> str:
        if attribute in self.attributes:
            return self.attributes[attribute]

    def getDomain(self):
        return self.domain

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
