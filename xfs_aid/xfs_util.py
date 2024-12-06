# coding:utf-8

import os
from typing import Dict
from typing import List


def is_mount_device(device: str) -> bool:
    with open("/etc/mtab", "r") as rhdl:
        if device in rhdl.read():
            return True
    return False


def is_empty_directory(dir: str) -> bool:
    return not os.path.exists(dir) or len(os.listdir(dir)) == 0


class xfs_kv(Dict[str, str]):

    def __init__(self, text: str) -> None:
        super().__init__()
        self.__text: str = text
        for item in text.splitlines():
            key_value: List[str] = [i.strip() for i in item.split("=", 1)]
            if len(key_value) == 2:
                key, value = key_value
                self[key] = value

    @property
    def text(self) -> str:
        return self.__text
