#! /usr/bin/env python3

import argparse
import os
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
        for lib in [
            'libwebsockets.dylib',
            'libjson-c.dylib',
            'libuv.dylib',
            'libssl.dylib',
            'libcrypto.dylib',
        ]:
            src_path = pathlib.Path('/usr/local/lib') / lib
            dst_path = LIB_PATH / name
            print(f'copy {src_path} to {dst_path}')
            shutil.copyfile(src_path, dst_path, follow_symlinks=True)


def build():
    copy_bin()

    import build.__main__
    import wheel.bdist_wheel

    tag = wheel.bdist_wheel.get_platform(pathlib.Path(__file__).parent)
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
