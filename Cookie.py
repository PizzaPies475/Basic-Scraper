from datetime import datetime, timedelta

dayOfWeekList = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class Cookie:

    def __init__(self, cookieName: str, domain, cookieValue=None, cookieAttributes=None):
        assert (type(cookieName) == str and cookieValue is None and cookieAttributes) is None or (
                type(cookieName) == str and type(cookieValue) == str and type(cookieAttributes) == dict)
        if cookieValue is not None:
            self.domain = domain
            self.name = cookieName
            self.value = cookieValue
            self.attributes = cookieAttributes
        else:
            cookieList = cookieName.split()
            self.name = cookieList[0].split('=')[0]
            self.value = cookieList[0].split('=')[1].removesuffix(';')
            self.attributes = dict()
            i = 1
            maxAgeFlag = False
            while i in range(1, len(cookieList)):
                if 'Max-Age' in cookieList[i]:
                    day_name = dayOfWeekList[datetime.today().weekday()]
                    maxAgeValue = int(cookieList[i][8:-1])
                    maxAgeHours = int(maxAgeValue/360)
                    maxAgeMinutes = int((maxAgeValue - maxAgeHours * 360) / 60)
                    maxAgeSeconds = (maxAgeValue - maxAgeHours * 360 - maxAgeMinutes*60) % 60
                    maxAgeTime = str(maxAgeHours).rjust(2, '0') + ':' + str(maxAgeMinutes).rjust(2, '0') + ':' + str(maxAgeSeconds).rjust(2, '0')
                    maxAgeToAdd = datetime.strptime(maxAgeTime, '%H:%M:%S')
                    maxAgeDate = datetime.now() + timedelta(hours=maxAgeToAdd.hour, minutes=maxAgeToAdd.minute, seconds=maxAgeToAdd.second)
                    self.attributes['expires'] = maxAgeDate.strftime(day_name + ", %d-%b-%Y %H:%M:%S GMT")
                    i += 2
                    maxAgeFlag = True
                elif maxAgeFlag and 'expires' in cookieList[i]:
                    i += 4
                elif 'expires' in cookieList[i]:
                    self.attributes['expires'] = cookieList[i][8:] + ' ' + cookieList[i + 1] + ' ' + cookieList[
                        i + 2] + ' ' + cookieList[i + 3][:-1]
                    i += 4
                elif '=' in cookieList[i]:
                    self.attributes[cookieList[i].split('=')[0]] = cookieList[i].split('=')[1].removesuffix(';')
                    i += 1
                else:
                    self.attributes[cookieList[i].removesuffix(';')] = True
                    i += 1
            if 'path' not in self.attributes and 'Path' not in self.attributes:  # TODO Learn about path and correct as needed.
                self.attributes['path'] = '/'

    def getName(self):
        return self.name

    def getValue(self):
        return self.value

    def getAttributes(self):
        return self.attributes

    def getAttribute(self, attribute):
        if attribute in self.attributes:
            return self.attributes[attribute]

    def getDomain(self):
        return self.domain

    # Returns True if the current time is later than the 'expires' attribute value
    #   (which is formatted as HTTP time, see getCurrHttpTime comment) of the given cookie.
    # If the cookie doesn't have an 'expires' attribute, the function returns False (duh).
    def isExpired(self):
        if self.getAttribute('expires'):
            return datetime.strptime(self.getAttribute('expires')[5:], "%d-%b-%Y %H:%M:%S GMT") < datetime.now()
        else:
            return False

    def __str__(self):
        return self.name + '=' + self.value
