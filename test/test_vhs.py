import logging
import pathlib

import vhs

import pytest


@pytest.fixture(scope='session', autouse=True)
def setup_logging():
    vhs.logger.setLevel(logging.DEBUG)


def test_bin_path_not_empty():
    bin_path = pathlib.Path(vhs.__file__).parent / 'bin'
    files = {f.name for f in bin_path.iterdir()}
    assert files == {'vhs', 'ttyd', 'ffmpeg'}, (
        f'{bin_path} should contain vhs executable and its dependencies. '
        f'if you\'re developing locally, you need to install VHS on your system, '
        f'then run `./build_wrapper.py copy_bin`'
    )


def test_vhs_inline(tmpdir):
    tmpdir = pathlib.Path(tmpdir)
    output = tmpdir / 'output.txt'

    vhs.vhs_inline(
        f'Output `{output}`\n'
        f'Type `echo "test"`\n'
        f'Enter\n',
        output_path=tmpdir / 'output.gif',  # vhs ascii requires -o .gif
        quiet=False,
    )

    output_text = output.read_text()
    assert output_text == (
        '> echo "test"\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '────────────────────────────────────────────────────────────────────────────────\n'
        '> echo "test"\n'
        'test\n'
        '>\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '────────────────────────────────────────────────────────────────────────────────\n'
    )


def test_vhs_inline_gif(tmpdir):
    output = pathlib.Path(tmpdir) / 'output.gif'

    vhs.vhs_inline(
        f'Type `echo "test"`\n'
        f'Enter\n',
        output_path=output,
        quiet=False,
    )

    assert output.exists()
    assert output.is_file()
    assert output.stat().st_size > 1204


def test_vhs_inline_env_and_cwd(tmpdir):
    tmpdir = pathlib.Path(tmpdir)

    cwd = tmpdir / 'cwd'
    cwd.mkdir()
    cwd.joinpath('this_is_expected_cwd').touch()

    output = tmpdir / 'output.txt'

    vhs.vhs_inline(
        f'Output `{output}`\n'
        f'Type `echo $XXX; ls`\n'
        f'Enter\n',
        output_path=tmpdir / 'output.gif',  # vhs ascii requires -o .gif
        env={'XXX': 'YYY'},
        cwd=cwd,
    )

    output_text = output.read_text()
    assert output_text == (
        '> echo $XXX; ls\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '────────────────────────────────────────────────────────────────────────────────\n'
        '> echo $XXX; ls\n'
        'YYY\n'
        'this_is_expected_cwd\n'
        '>\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '\n'
        '────────────────────────────────────────────────────────────────────────────────\n'
    )
