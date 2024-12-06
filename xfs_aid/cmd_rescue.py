# coding:utf-8

from typing import Optional
from typing import Sequence

from xarg import add_command
from xarg import argp
from xarg import commands
from xarg import run_command

from .attribute import __description__
from .attribute import __urlhome__
from .attribute import __version__
from .xfs_aidkit import xfs_rescue


@add_command("xfs-rescue", help="rescue an XFS filesystem device")
def add_cmd_file(_arg: argp):
    _arg.add_argument(dest="device", type=str, metavar="DEV",
                      help="XFS filesystem device")
    _arg.add_argument(dest="target", type=str, metavar="DIR",
                      help="target directory")


@run_command(add_cmd_file)
def run_cmd_file(cmds: commands) -> int:
    handler: xfs_rescue = xfs_rescue(device=cmds.args.device,
                                     basedir=cmds.args.target)
    for obj in handler.xfiles:
        cmds.stdout(f"rebuild inode {obj.ino} size {obj.size} => {obj.target}")
        if not obj.rebuild():
            cmds.stderr(f"rebuild inode {obj.ino} => {obj.target} failed")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    cmds = commands()
    cmds.version = __version__
    return cmds.run(
        root=add_cmd_file,
        argv=argv,
        description=__description__,
        epilog=f"For more, please visit {__urlhome__}.")
