# coding:utf-8

import os
from typing import Any
from typing import BinaryIO
from typing import Generator
from typing import Optional

from .exception import XfsAidDirectoryNotEmptyException
from .exception import XfsAidTargetExistsException
from .exception import XfsCmdException
from .xfs_debug import xfs_blockmap
from .xfs_debug import xfs_content
from .xfs_debug import xfs_db
from .xfs_debug import xfs_inode
from .xfs_util import is_empty_directory


class xfs_file(object):
    def __init__(self, device: str, inode_number: int):
        debug: xfs_db = xfs_db(device=device)
        inode: xfs_inode = debug.inode(inode_number)
        assert inode.v3_inumber == inode_number, f"inode number {inode_number} error"  # noqa:E501
        self.__debug: xfs_db = debug
        self.__inode: xfs_inode = inode
        self.__inode_number: int = inode_number
        self.__file_size: int = inode.core_size

    @property
    def ino(self) -> int:
        """inode number"""
        return self.__inode_number

    @property
    def debug(self) -> xfs_db:
        return self.__debug

    @property
    def inode(self) -> xfs_inode:
        return self.__inode

    @property
    def size(self) -> int:
        """file size"""
        return self.__file_size

    @property
    def damaged(self) -> bool:
        return not self.is_good()

    @property
    def extents(self) -> Generator[xfs_blockmap, Any, None]:
        return self.debug.bmap(inode_number=self.ino)

    def is_good(self) -> bool:
        good: bool = True
        if sum(e.count for e in self.extents) * self.debug.blocksize < self.size:  # noqa:E501
            good = False  # check extents blocks error
        return good

    def raw(self, stream: BinaryIO) -> bool:
        """read raw date from an XFS file"""
        with open(self.debug.device, "rb") as rhdl:
            offset: int = 0
            blocksize: int = self.debug.blocksize
            for extent in self.extents:
                assert extent.blocksize == blocksize, f"inode {self.ino} blocksize {extent.blocksize} error"  # noqa:E501
                assert extent.startoffset * blocksize == offset, f"inode {self.ino} offset {offset} error"  # noqa:E501
                rhdl.seek(extent.startblock * blocksize, 0)
                for _ in range(extent.count):
                    size: int = min(self.size - offset, blocksize)
                    offset += size
                    assert offset <= self.size, f"inode {self.ino} offset {offset} (size {self.size}) error"  # noqa:E501
                    data: bytes = rhdl.read(size)
                    stream.write(data)
                    stream.flush()
            assert self.size == offset, f"inode {self.ino} offset {offset} (size {self.size}) error"  # noqa:E501
        return True

    def dump(self, target: str) -> bool:
        """dump raw data to target file"""
        if os.path.exists(target):
            raise XfsAidTargetExistsException(target)
        try:
            with open(target, "wb") as whdl:
                self.raw(stream=whdl)
        except Exception:
            os.remove(target)
            return False
        return True


class xfs_scan(object):
    def __init__(self, device: str):
        self.__debug: xfs_db = xfs_db(device=device)
        self.__max_inode_number: int = 0
        self.__max_inode_dispaly: int = 10

    @property
    def debug(self):
        return self.__debug

    @property
    def max_ino(self) -> int:
        """inode number maximum"""
        return self.__max_inode_number

    @max_ino.setter
    def max_ino(self, value: int):
        if value > self.__max_inode_number:
            self.__max_inode_number = value
            self.__max_inode_dispaly = max(len(str(value)), 10)

    @property
    def max_ino_display(self) -> int:
        """inode number display character maximum"""
        return self.__max_inode_dispaly

    @property
    def objects(self) -> Generator[xfs_content, Any, None]:
        """all objects"""

        def dfs(content: Optional[xfs_content] = None):
            if content is not None:
                path: str = content.path
                inode: Optional[int] = content.ino
                self.max_ino = max(self.max_ino, inode)
            else:  # start from root
                path: str = "/"  # start from root
                inode: Optional[int] = None

            try:
                for content in self.debug.ls(path=path, inode=inode):
                    if content.is_dir:  # deep first
                        yield from dfs(content)
                    elif content.is_file:
                        xfile: xfs_file = xfs_file(device=self.debug.device,
                                                   inode_number=content.ino)
                        if xfile.damaged:
                            content.damaged = True
                    yield content
            except XfsCmdException:
                if content is not None:
                    content.damaged = True

        yield from dfs()

    @property
    def damaged(self) -> Generator[xfs_content, Any, None]:
        """all damaged objects"""
        for obj in self.objects:
            if obj.damaged:
                yield obj

    @property
    def files(self) -> Generator[xfs_content, Any, None]:
        """all good files"""
        for obj in self.objects:
            if obj.is_file and not obj.damaged:
                yield obj

    def show(self, content: xfs_content) -> str:
        # health: str = "bad" if content.damaged else "good"
        inode: str = str(content.ino).ljust(self.max_ino_display)
        filetype: str = content.filetype.ljust(10)
        return f"{inode} {filetype} {content.path}"


class xfs_rescue(xfs_scan):

    class _file(xfs_file):
        def __init__(self, device: str, inode_number: int, target: str):
            super().__init__(device=device, inode_number=inode_number)
            self.__target: str = target

        @property
        def target(self) -> str:
            return self.__target

        def rebuild(self) -> bool:
            """rebuild file"""
            dir: str = os.path.dirname(self.target)
            if not os.path.exists(dir):
                os.makedirs(dir)
            return self.dump(target=self.target)

    def __init__(self, device: str, basedir: str):
        if not is_empty_directory(dir=basedir):
            raise XfsAidDirectoryNotEmptyException(basedir)
        super().__init__(device=device)
        self.__basedir: str = basedir

    @property
    def base(self) -> str:
        """base directory"""
        return self.__basedir

    @property
    def xfiles(self) -> Generator[_file, Any, None]:
        for file in self.files:
            target: str = os.path.join(self.base, file.path[1:])
            yield self._file(device=self.debug.device,
                             inode_number=file.ino,
                             target=target)
