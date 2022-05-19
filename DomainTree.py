from httpUtil import getDomainFromUrl, isValidURL


class DomainTree:
    def __init__(self, domain: str):
        self.root: DirectoryNode = DirectoryNode(domain)
        self.size = 1
        self.UrlDict = {}

    def put(self, URL: str):
        if isValidURL(URL) and (getDomainFromUrl(URL) in self.root.URL):
            if URL in self.UrlDict:
                return self.UrlDict[URL]
            else:
                currURL: str = URL.removeprefix("https://")
                currURL = currURL.removeprefix("http://")
                currURL = currURL.removeprefix(self.root.URL)
                dirPathList: list[str] = currURL.split("/")
                currNode: DirectoryNode = self.root
                currPath: str = self.root.URL
                for dirName in dirPathList:
                    if dirName in currNode.children:
                        currNode = currNode.children[dirName]
                        currPath += "/" + dirName
                    else:
                        newNode = DirectoryNode(currPath + "/" + dirName, currNode)
                        currNode.children[dirName] = newNode
                        currNode = newNode
                        currPath += "/" + dirName
                        self.size += 1
                currNode.isURL = True
                self.UrlDict[URL] = currNode
                return currNode

    def get(self, URL: str):
        if URL in self.UrlDict:
            return self.UrlDict[URL]
        else:
            return None

    def __contains__(self, URL: str):
        return URL in self.UrlDict


class DirectoryNode:
    def __init__(self, URL: str, parent=None, isURL: bool = False):
        """
        Initializes a new DirectoryNode with the given URL and creates an empty children dictionary.
        """
        self.URL: str = URL
        self.children: {str: DirectoryNode} = {}
        self.parent: DirectoryNode = parent
        self.isURL: bool = isURL
