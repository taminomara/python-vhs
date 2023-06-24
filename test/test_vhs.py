import logging
import os
import pathlib
import shutil

import pytest

import vhs


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
    res = _run_inline(
        detected_vhs,
        f"""
        Type "which vhs"
        Enter
        Type "which ttyd"
        Enter
        Type "which ffmpeg"
        Enter
        """,
        tmpdir,
    )

    assert _path_in_res(vhs_path, res)
    assert _path_in_res(ttyd_path, res)
    assert _path_in_res(ffmpeg_path, res)


def _path_in_res(s, res) -> bool:
    s = str(s).replace("\\", "/").lower()
    if s.startswith("c:/"):
        s = s[3:]
    if s.endswith(".exe"):
        s = s[:-4]
    return s in str(res).lower().replace("\n", "").replace("\r", "")


def _run(detected_vhs: vhs.Vhs, tape: str, tmpdir, **kwargs) -> str:
    tape = f"Output `{tmpdir / 'out.txt'}`\n" + tape

    tape_file = tmpdir / "input.tape"
    with open(tape_file, "w") as f:
        f.write(tape)

    detected_vhs.run(tape_file, tmpdir / "out.gif", **kwargs)

    with open(tmpdir / "out.txt") as f:
        return f.read()


def _run_inline(detected_vhs: vhs.Vhs, tape: str, tmpdir, **kwargs) -> str:
    tape = f"Output `{tmpdir / 'out.txt'}`\n" + tape

    detected_vhs.run_inline(tape, tmpdir / "out.gif", **kwargs)

    with open(tmpdir / "out.txt") as f:
        return f.read()


@pytest.mark.parametrize("runner", [_run, _run_inline])
def test_env(tmpdir, runner):
    res = runner(
        vhs.resolve(cache_path=tmpdir, env={**os.environ, "SOME_VAR": "SOME_TEXT"}),
        f"""
        Type "echo $SOME_VAR"
        Enter
        """,
        tmpdir,
    )

    assert "SOME_TEXT" in res

    res = runner(
        vhs.resolve(cache_path=tmpdir, env={**os.environ, "SOME_VAR_1": "SOME_TEXT"}),
        f"""
        Type "echo $SOME_VAR_1"
        Enter
        Type "echo $SOME_VAR_2"
        Enter
        """,
        tmpdir,
        env={**os.environ, "SOME_VAR_2": "OTHER_TEXT"},
    )

    assert "SOME_TEXT" not in res
    assert "OTHER_TEXT" in res


@pytest.mark.parametrize("runner", [_run, _run_inline])
def test_cwd(tmpdir, runner):
    cwd1 = tmpdir / "cwd1"
    cwd1.mkdir()

    res = runner(
        vhs.resolve(cache_path=tmpdir, cwd=cwd1),
        f"""
        Type "pwd"
        Enter
        """,
        tmpdir,
    )

    assert _path_in_res(cwd1, res)

    cwd2 = tmpdir / "cwd2"
    cwd2.mkdir()

    res = runner(
        vhs.resolve(cache_path=tmpdir, cwd=cwd1),
        f"""
        Type "pwd"
        Enter
        """,
        tmpdir,
        cwd=cwd2,
    )

    assert not _path_in_res(cwd1, res)
    assert _path_in_res(cwd2, res)
