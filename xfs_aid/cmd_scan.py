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
from .xfs_aidkit import xfs_scan


@add_command("all", help="list all contents in XFS filesystem")
def add_cmd_scan_all(_arg: argp):
    pass


@run_command(add_cmd_scan_all)
def run_cmd_scan_all(cmds: commands) -> int:
    scanner: xfs_scan = xfs_scan(device=cmds.args.device)
    for object in scanner.objects:
        cmds.stdout(scanner.show(object))
    return 0


@add_command("damaged", help="list all damaged contents in XFS filesystem")
def add_cmd_scan_damaged(_arg: argp):
    pass


@run_command(add_cmd_scan_damaged)
def run_cmd_scan_damaged(cmds: commands) -> int:
    scanner: xfs_scan = xfs_scan(device=cmds.args.device)
    for object in scanner.damaged:
        cmds.stdout(scanner.show(object))
    return 0


@add_command("files", help="list all files in XFS filesystem")
def add_cmd_scan_files(_arg: argp):
    pass


@run_command(add_cmd_scan_files)
def run_cmd_scan_files(cmds: commands) -> int:
    scanner: xfs_scan = xfs_scan(device=cmds.args.device)
    for file in scanner.files:
        cmds.stdout(scanner.show(file))
    return 0


@add_command("xfs-scan", help="scan XFS filesystem")
def add_cmd_scan(_arg: argp):
    _arg.add_argument(dest="device", type=str, metavar="DEV",
                      help="XFS filesystem device")


@run_command(add_cmd_scan, add_cmd_scan_all, add_cmd_scan_damaged,
             add_cmd_scan_files)
def run_cmd_scan(cmds: commands) -> int:
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    cmds = commands()
    cmds.version = __version__
    return cmds.run(
        root=add_cmd_scan,
        argv=argv,
        description=__description__,
        epilog=f"For more, please visit {__urlhome__}.")
