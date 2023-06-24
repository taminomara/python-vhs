import logging
import os
import pathlib
import shutil

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

    _do_vhs_test(
        detected_vhs,
        tmpdir,
        system_vhs,
        shutil.which("ttyd"),
        shutil.which("ffmpeg"),
    )


@pytest.mark.linux
def test_system_vhs_unavailable(tmpdir):
    detected_vhs = vhs.resolve(cache_path=tmpdir, env={"PATH": os.defpath})
    assert detected_vhs._vhs_path == pathlib.Path(tmpdir) / "vhs"
    assert detected_vhs._path.startswith(str(tmpdir))

    _do_vhs_test(
        detected_vhs,
        tmpdir,
        tmpdir / "vhs",
        tmpdir / "ttyd",
        tmpdir / "ffmpeg",
    )


@pytest.mark.darwin
@pytest.mark.win32
def test_system_vhs_unavailable_fail(tmpdir):
    with pytest.raises(vhs.VhsError, match=r"VHS is not installed on your system"):
        vhs.resolve(cache_path=tmpdir, env={"PATH": os.defpath})


@pytest.mark.linux
def test_system_vhs_outdated(tmpdir):
    detected_vhs = vhs.resolve(cache_path=tmpdir, min_version="9999.0.0")
    assert detected_vhs._vhs_path == pathlib.Path(tmpdir) / "vhs"
    assert detected_vhs._path.startswith(str(tmpdir))

    _do_vhs_test(
        detected_vhs,
        tmpdir,
        tmpdir / "vhs",
        tmpdir / "ttyd",
        tmpdir / "ffmpeg",
    )


@pytest.mark.darwin
@pytest.mark.win32
def test_system_vhs_outdated_fail(tmpdir):
    with pytest.raises(
        vhs.VhsError, match=r"but version 9999.0.0 or newer is required"
    ):
        vhs.resolve(cache_path=tmpdir, min_version="9999.0.0")


def _do_vhs_test(
    detected_vhs: vhs.Vhs,
    tmpdir,
    vhs_path,
    ttyd_path,
    ffmpeg_path,
):
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
        res = f.read().lower()

    assert _san_path(str(vhs_path)) in res
    assert _san_path(str(ttyd_path)) in res
    assert _san_path(str(ffmpeg_path)) in res


def _san_path(s: str) -> str:
    s = s.replace("\\", "/").lower()
    if s.startswith("c:/"):
        s = s[3:]
    if s.endswith(".exe"):
        s = s[:-4]
    return s


def test_reporter():
    pass
