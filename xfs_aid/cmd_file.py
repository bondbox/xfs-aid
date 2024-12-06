# coding:utf-8

import sys
from typing import Optional
from typing import Sequence

from xarg import add_command
from xarg import argp
from xarg import commands
from xarg import run_command

from .attribute import __description__
from .attribute import __urlhome__
from .attribute import __version__
from .xfs_aidkit import xfs_file


@add_command("bmap", help="print block mapping for an XFS file")
def add_cmd_file_bmap(_arg: argp):
    pass


@run_command(add_cmd_file_bmap)
def run_cmd_file_bmap(cmds: commands) -> int:
    file: xfs_file = xfs_file(device=cmds.args.device,
                              inode_number=cmds.args.inode)
    nblock: int = 0
    nextent: int = 0
    for extent in file.extents:
        cmds.stdout(extent.show())
        nblock += extent.count
        nextent += 1
    cmds.stdout(f"{file.size} bytes in {nextent} extents {nblock} blocks")
    return 0


@add_command("raw", help="read raw data for an XFS file")
def add_cmd_file_raw(_arg: argp):
    pass


@run_command(add_cmd_file_raw)
def run_cmd_file_raw(cmds: commands) -> int:
    file: xfs_file = xfs_file(device=cmds.args.device,
                              inode_number=cmds.args.inode)
    file.raw(stream=sys.stdout.buffer)
    return 0


@add_command("xfs-file", help="rescue an XFS file")
def add_cmd_file(_arg: argp):
    _arg.add_argument(dest="device", type=str, metavar="DEV",
                      help="XFS filesystem device")
    _arg.add_argument(dest="inode", type=int, metavar="INO",
                      help="the inode number of an XFS file")


@run_command(add_cmd_file, add_cmd_file_bmap, add_cmd_file_raw)
def run_cmd_file(cmds: commands) -> int:
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    cmds = commands()
    cmds.version = __version__
    return cmds.run(
        root=add_cmd_file,
        argv=argv,
        description=__description__,
        epilog=f"For more, please visit {__urlhome__}.")
