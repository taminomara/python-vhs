import pathlib
import shutil
import stat
import sys

BIN_PATH = pathlib.Path(__file__).parent / 'vhs' / 'bin'


def copy_bin():
    BIN_PATH.mkdir(exist_ok=True)
    for name in ['vhs', 'ttyd', 'ffmpeg']:
        cmd_path = shutil.which(name)
        if cmd_path is None:
            raise RuntimeError(f'unable to find executable {name}')
        dest_name = name
        if sys.platform == 'win32':
            dest_name += '.exe'
        dest_cmd_path = BIN_PATH / dest_name
        print(f'copy {cmd_path} to {dest_cmd_path}')
        shutil.copyfile(cmd_path, dest_cmd_path, follow_symlinks=True)
        dest_cmd_path.chmod(dest_cmd_path.stat().st_mode | stat.S_IEXEC)


def build_wheel():
    import build.__main__
    import wheel.bdist_wheel

    tag = wheel.bdist_wheel.get_platform(pathlib.Path(__file__).parent)
    build.__main__.main([
        '--wheel', f'-C=--build-option=--plat {tag}',
    ])


if __name__ == '__main__':
    copy_bin()
    build_wheel()
