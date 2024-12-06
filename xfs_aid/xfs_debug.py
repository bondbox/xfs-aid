# coding:utf-8

import os
import re
import subprocess
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional

from xarg import cmds

from .exception import DevIsMountException
from .exception import XfsAgnoException
from .exception import XfsBmapException
from .exception import XfsCmdException
from .xfs_util import is_mount_device
from .xfs_util import xfs_kv


class xfs_superblock(xfs_kv):
    """ag superblock"""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.__magicnum: str = self["magicnum"]
        self.__blocksize: int = int(self["blocksize"])
        self.__agcount: int = int(self["agcount"])
        self.__agblocks: int = int(self["agblocks"])

    @property
    def magicnum(self) -> str:
        return self.__magicnum

    @property
    def blocksize(self) -> int:
        return self.__blocksize

    @property
    def agcount(self) -> int:
        return self.__agcount

    @property
    def agblocks(self) -> int:
        return self.__agblocks


class xfs_inode(xfs_kv):
    """inode"""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.__core_size: int = int(self["core.size"])
        self.__v3_inumber: int = int(self["v3.inumber"])

    @property
    def core_size(self) -> int:
        return self.__core_size

    @property
    def v3_inumber(self) -> int:
        return self.__v3_inumber


class xfs_content(object):
    """xfs_db ls object"""

    def __init__(self, path: str, text: str) -> None:
        # directory cookie, inode number, file type, hash, name length, name.
        output: List[str] = [i.strip() for i in text.strip().split(maxsplit=4)]
        cmds.logger.debug(f"xfs_db_content entry: {text} => {output}")
        self.__directory_cookie: int = int(output[0])
        self.__inode_number: int = int(output[1])
        self.__file_type: str = output[2]
        self.__hash: str = output[3]
        # Handle name length and name, name may contain spaces
        index: int = output[4].index(" ")
        start: int = index + 1
        name_length: int = int(output[4][:index].strip())  # bytes
        name_bytes: bytes = output[4][start:].encode()
        name: str = name_bytes[:name_length].decode()
        self.__name_length: int = name_length
        self.__name: str = name
        self.__path: str = os.path.join(path, name)
        self.__damaged: bool = False

    @property
    def directory_cookie(self) -> int:
        return self.__directory_cookie

    @property
    def ino(self) -> int:
        """inode number"""
        return self.__inode_number

    @property
    def filetype(self) -> str:
        """file type"""
        return self.__file_type

    @property
    def is_dir(self) -> bool:
        return self.filetype == "directory"

    @property
    def is_file(self) -> bool:
        return self.filetype == "regular"

    @property
    def hash(self) -> str:
        return self.__hash

    @property
    def nlen(self) -> int:
        """name length"""
        return self.__name_length

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> str:
        return self.__path

    @property
    def damaged(self) -> bool:
        return self.__damaged

    @damaged.setter
    def damaged(self, value: bool):
        self.__damaged = value


class xfs_blockmap(object):
    """xfs_db bmap object"""

    PATTERN = re.compile(r'data offset (?P<offset>\d+) startblock (?P<startblock>\d+) \((?P<agno>\d+)/(?P<agbno>\d+)\) count (?P<blockcount>\d+) flag (?P<extentflag>\d+)')  # noqa:E501

    def __init__(self, order: int, blocksize: int, text: str) -> None:
        # noqa:E501 data offset <offset> startblock <startblock> (<agno>/<ag_startblock>) count <blockcount> flag <int>
        items: Optional[re.Match[str]] = self.PATTERN.match(text)
        if items is None:
            raise XfsBmapException(text=text)
        blocks: int = int(items.group("blockcount"))
        self.__extent: int = order
        self.__blockcount: int = blocks
        self.__blocksize: int = blocksize
        self.__startoffset: int = int(items.group("offset"))
        self.__endoffset: int = self.__startoffset + blocks
        self.__startblock: int = int(items.group("startblock"))
        self.__endblock: int = self.__startblock + blocks
        self.__ag_number: int = int(items.group("agno"))
        self.__ag_startblock: int = int(items.group("agbno"))
        self.__extentflag: int = int(items.group("extentflag"))

    @property
    def extent(self) -> int:
        return self.__extent

    @property
    def blocksize(self) -> int:
        return self.__blocksize

    @property
    def count(self) -> int:
        """block count"""
        return self.__blockcount

    @property
    def startoffset(self) -> int:
        """first block offset starting from file"""
        return self.__startoffset

    @property
    def endoffset(self) -> int:
        """last block offset starting from file"""
        return self.__endoffset

    @property
    def startblock(self) -> int:
        """first block offset starting from device"""
        return self.__startblock

    @property
    def endblock(self) -> int:
        """last block offset starting from device"""
        return self.__endblock

    @property
    def agno(self) -> int:
        """ag number"""
        return self.__ag_number

    @property
    def agbno(self) -> int:
        """first block offset starting from ag"""
        return self.__ag_startblock

    @property
    def flag(self) -> int:
        """extent flag"""
        return self.__extentflag

    def show(self) -> str:
        """format output

        Each line of the listings takes the following form:
            extent: [startoffset..endoffset]: startblock..endblock
        """
        return f"{self.extent}: [{self.startoffset}..{self.endoffset}]: {self.startblock}..{self.endblock}"  # noqa:E501


class xfs_db(object):
    def __init__(self, device: str) -> None:
        if is_mount_device(device=device):
            raise DevIsMountException(device)
        self.__device: str = device
        self.__inodes: Dict[int, xfs_inode] = {}
        self.__superblocks: Dict[int, xfs_superblock] = {}

    @property
    def device(self) -> str:
        return self.__device

    @property
    def primary_sb(self) -> xfs_superblock:
        """AG 0 is primary"""
        return self.sb(0)

    @property
    def blocksize(self) -> int:
        return self.primary_sb.blocksize

    @property
    def agcount(self) -> int:
        return self.primary_sb.agcount

    def command(self, *cmds: str) -> str:
        para: str = " ".join(f"-c '{cmd}'" for cmd in cmds)
        args: str = f"xfs_db {self.device} {para}"
        comp: subprocess.CompletedProcess = subprocess.run(
            args=args, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if comp.returncode != 0:
            raise XfsCmdException(comp.returncode, args)
        return comp.stdout

    def sb(self, agno: int) -> xfs_superblock:
        # check agno at [0, agcount), ag 0 is primary
        if agno != 0 and agno not in range(self.agcount):
            raise XfsAgnoException(agno=agno, expected=self.agcount)
        if agno not in self.__superblocks:
            stdout: str = self.command(f"sb {agno}", "print")
            self.__superblocks[agno] = xfs_superblock(stdout)
        return self.__superblocks[agno]

    def inode(self, inode_number: int) -> xfs_inode:
        if inode_number not in self.__inodes:
            stdout: str = self.command(f"inode {inode_number}", "print")
            self.__inodes[inode_number] = xfs_inode(stdout)
        return self.__inodes[inode_number]

    def ls(self, path: str, inode: Optional[int] = None
           ) -> Generator[xfs_content, Any, None]:
        """List the contents of a directory."""
        stdout: str = self.command(f"ls {path}") if inode is None else\
            self.command(f"inode {inode}", "ls")

        for line in stdout.splitlines()[1:]:
            content: xfs_content = xfs_content(path, line)
            if content.name in [".", ".."]:
                continue
            yield content

    def bmap(self, inode_number: int) -> Generator[xfs_blockmap, Any, None]:
        """Show the block map for the current inode."""
        for index, value in enumerate(self.command(f"inode {inode_number}", "bmap").splitlines()):  # noqa:E501
            yield xfs_blockmap(order=index, blocksize=self.blocksize, text=value)  # noqa:E501
