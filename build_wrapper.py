#! /usr/bin/env python3

import argparse
import os
import re
import subprocess
import pathlib
import shutil
import stat
import sys


BIN_PATH = pathlib.Path(__file__).parent / 'src' / 'vhs' / 'bin'
LIB_PATH = pathlib.Path(__file__).parent / 'src' / 'vhs' / 'lib'


def copy_bin():
    BIN_PATH.mkdir(exist_ok=True)
    LIB_PATH.mkdir(exist_ok=True)

    for name in ['vhs', 'ttyd', 'ffmpeg']:
        src_path = shutil.which(name)
        if src_path is None:
            raise RuntimeError(
                f'unable to find executable {name}. make sure VHS '
                f'is installed and available through your PATH'
            )

        dst_path = BIN_PATH / (name + '.exe' if sys.platform == 'win32' else name)

        print(f'copy {src_path} to {dst_path}')
        shutil.copyfile(src_path, dst_path, follow_symlinks=True)

        dst_path.chmod(dst_path.stat().st_mode | stat.S_IEXEC)

    if sys.platform == 'darwin':
        ttyd_run = subprocess.run(
            ['ttyd', '--version'],
            env={**os.environ, 'DYLD_PRINT_LIBRARIES': 'YES'},
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
        )

        for line in ttyd_run.stderr.splitlines():
            if match := re.match(rb'^.*?(/usr/local/Cellar/.+)$', line):
                src_path = pathlib.Path(match.group(1).decode())

                if src_path.name == 'ttyd':
                    continue

                dst_path = LIB_PATH / src_path.name

                print(f'copy {src_path} to {dst_path}')
                shutil.copyfile(src_path, dst_path, follow_symlinks=True)

                name_components = dst_path.name.split('.')
                for i in [1, 2]:
                    name = '.'.join(name_components[:i]) + '.' + name_components[-1]
                    link_path = dst_path.parent / name
                    if not link_path.exists():
                        print(f'symlink {dst_path.parent / name} -> {dst_path}')
                        os.symlink(dst_path, dst_path.parent / name)


def build():
    copy_bin()

    import build.__main__
    import wheel.bdist_wheel

    tag = wheel.bdist_wheel.get_platform(None)
    build.__main__.main([
        '--wheel', f'-C=--build-option=--plat {tag}',
    ])


def main():
    parser = argparse.ArgumentParser(description='VHS building helper')
    commands = parser.add_subparsers(title='command', dest='command', required=True)
    commands.add_parser('build').set_defaults(func=build)
    commands.add_parser('copy_bin').set_defaults(func=copy_bin)

    parser.parse_args().func()


if __name__ == '__main__':
    main()
