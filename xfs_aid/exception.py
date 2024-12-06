# coding:utf-8


class XfsAidException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class DevIsMountException(XfsAidException):
    def __init__(self, device: str):
        super().__init__(f"Device {device} is a mounted filesystem")


class XfsCmdException(XfsAidException):
    def __init__(self, returncode: int, command: str):
        super().__init__(f"Failed ({returncode}) to run command: {command}")


class XfsAgnoException(XfsAidException):
    def __init__(self, agno: int, expected: int):
        super().__init__(f"Illegal AG (count {expected}) number: {agno}")


class XfsBmapException(XfsAidException):
    def __init__(self, text: str):
        super().__init__(f"Failed to parse bmap: {text}")


class XfsAidTargetExistsException(XfsAidException):
    def __init__(self, target: str):
        super().__init__(f"Taget '{target}' already exists")


class XfsAidDirectoryNotEmptyException(XfsAidException):
    def __init__(self, dir: str):
        super().__init__(f"Directory '{dir}' is not empty")
