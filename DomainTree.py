from httpUtil import getDomainFromUrl, isValidURL


class DomainTree:
    def __init__(self, domain: str):
        self.root: DirectoryNode = DirectoryNode(domain)

    def put(self, URL: str):
        if isValidURL(URL) and (getDomainFromUrl(URL) in self.root.URL):
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
            currNode.isURL = True
            return currNode


class DirectoryNode:
    def __init__(self, URL: str, parent=None, isURL: bool = False):
        """
        Initializes a new DirectoryNode with the given URL and creates an empty children dictionary.
        """
        self.URL: str = URL
        self.children: {str: DirectoryNode} = {}
        self.parent: DirectoryNode = parent
        self.isURL: bool = isURL
