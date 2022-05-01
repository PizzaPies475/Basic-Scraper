
# Clears file if the file already exists, or creates a new file with the given file name.
# If there is data to be written, writes bytes/string to the file, as per the writeType argument.
# Write types that can be used are "wb", "a" and "w".
# Using other types will raise a ValueError exception.
def clearFileAndWrite(fileName, writeType, data=None):
    with open(fileName, "w"):
        pass
    if data is not None:
        if writeType == 'wb':
            with open(fileName, writeType) as toWriteTo:
                toWriteTo.write(data)
        elif writeType == 'a' or writeType == 'w':
            with open(fileName, writeType, encoding="ISO-8859-1") as toWriteTo:
                toWriteTo.write(data)
        else:
            raise ValueError('Only "wb", "a" and "w" writeTypes accepted.')
