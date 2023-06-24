import logging
import os
import pathlib
import shutil
import sys

import vhs

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    vhs._logger.setLevel(logging.DEBUG)


def test_system_vhs(tmpdir):
    system_vhs = shutil.which("vhs")
    assert system_vhs is not None, "vhs should be installed on your system to run tests"

    detected_vhs = vhs.resolve(cache_path=tmpdir)
    assert detected_vhs._vhs_path == pathlib.Path(system_vhs)

    if sys.platform == "win32":
        res = _do_vhs_test_win(detected_vhs, tmpdir)

        assert "hello world" in res
    else:
        detected_vhs.run_inline(
            f"""
            Output "{tmpdir / 'out.txt'}"
            Type "which vhs"
            Enter
            Type "which ttyd"
            Enter
            Type "which ffmpeg"
            Enter
            """,
            tmpdir / "out.gif",
        )

        with open(tmpdir / "out.txt") as f:
            res = f.read()

        assert system_vhs in res
        assert shutil.which("ttyd") in res
        assert shutil.which("ffmpeg") in res


@pytest.mark.linux
def test_system_vhs_unavailable(tmpdir):
    detected_vhs = vhs.resolve(cache_path=tmpdir, env={"PATH": os.defpath})
    assert detected_vhs._vhs_path == pathlib.Path(tmpdir) / "vhs"
    assert detected_vhs._path.startswith(str(tmpdir))

    detected_vhs.run_inline(
        f"""
        Output "{tmpdir / 'out.txt'}"
        Type "which vhs"
        Enter
        Type "which ttyd"
        Enter
        Type "which ffmpeg"
        Enter
        """,
        tmpdir / "out.gif",
    )

    with open(tmpdir / "out.txt") as f:
        res = f.read()

    assert str(tmpdir / "vhs") in res
    assert str(tmpdir / "ttyd") in res
    assert str(tmpdir / "ffmpeg") in res


@pytest.mark.darwin
@pytest.mark.win32
def test_system_vhs_unavailable_darwin(tmpdir):
    with pytest.raises(vhs.VhsError, match=r"VHS is not installed on your system"):
        vhs.resolve(cache_path=tmpdir, env={"PATH": os.defpath})


@pytest.mark.linux
def test_system_vhs_outdated(tmpdir):
    detected_vhs = vhs.resolve(cache_path=tmpdir, min_version="9999.0.0")
    assert detected_vhs._vhs_path == pathlib.Path(tmpdir) / "vhs"
    assert detected_vhs._path.startswith(str(tmpdir))

    res = _do_vhs_test(detected_vhs, tmpdir)

    assert str(tmpdir / "vhs") in res
    assert str(tmpdir / "ttyd") in res
    assert str(tmpdir / "ffmpeg") in res


@pytest.mark.darwin
@pytest.mark.win32
def test_system_vhs_outdated_darwin(tmpdir):
    with pytest.raises(
        vhs.VhsError, match=r"but version 9999.0.0 or newer is required"
    ):
        vhs.resolve(cache_path=tmpdir, min_version="9999.0.0")


def _do_vhs_test_win(detected_vhs: vhs.Vhs, tmpdir):
    detected_vhs.run_inline(
        f"""
        Output "{tmpdir / 'out.txt'}"
        Type "echo 'hello world'"
        Enter
        """,
        tmpdir / "out.gif",
    )

    with open(tmpdir / "out.txt") as f:
        return f.read()


def test_reporter():
    pass


# def test_vhs_inline(tmpdir):
#     tmpdir = pathlib.Path(tmpdir)
#     output = tmpdir / 'output.txt'
#
#     vhs.vhs_inline(
#         f'Output `{output}`\n'
#         f'Type `echo "test"`\n'
#         f'Enter\n',
#         output_path=tmpdir / 'output.gif',  # vhs ascii requires -o .gif
#         quiet=False,
#     )
#
#     output_text = output.read_text()
#     assert output_text == (
#         '> echo "test"\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '────────────────────────────────────────────────────────────────────────────────\n'
#         '> echo "test"\n'
#         'test\n'
#         '>\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '────────────────────────────────────────────────────────────────────────────────\n'
#     )
#
#
# def test_vhs_inline_gif(tmpdir):
#     output = pathlib.Path(tmpdir) / 'output.gif'
#
#     vhs.vhs_inline(
#         f'Type `echo "test"`\n'
#         f'Enter\n',
#         output_path=output,
#         quiet=False,
#     )
#
#     assert output.exists()
#     assert output.is_file()
#     assert output.stat().st_size > 1204
#
#
# def test_vhs_inline_env_and_cwd(tmpdir):
#     tmpdir = pathlib.Path(tmpdir)
#
#     cwd = tmpdir / 'cwd'
#     cwd.mkdir()
#     cwd.joinpath('this_is_expected_cwd').touch()
#
#     output = tmpdir / 'output.txt'
#
#     vhs.vhs_inline(
#         f'Output `{output}`\n'
#         f'Type `echo $XXX; ls`\n'
#         f'Enter\n',
#         output_path=tmpdir / 'output.gif',  # vhs ascii requires -o .gif
#         env={'XXX': 'YYY'},
#         cwd=cwd,
#     )
#
#     output_text = output.read_text()
#     assert output_text == (
#         '> echo $XXX; ls\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '────────────────────────────────────────────────────────────────────────────────\n'
#         '> echo $XXX; ls\n'
#         'YYY\n'
#         'this_is_expected_cwd\n'
#         '>\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '\n'
#         '────────────────────────────────────────────────────────────────────────────────\n'
#     )


def test_tmp():
    import tempfile

    tempfile.tempdir = None
    print(tempfile.gettempdir())
