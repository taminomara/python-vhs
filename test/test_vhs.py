# pyright: reportPrivateUsage=false

import functools
import logging
import os
import pathlib
import shutil
import sys

import github
import pytest

import vhs

vhs._get_repo = functools.lru_cache()(vhs._get_repo)
vhs._get_releases = functools.lru_cache()(vhs._get_releases)


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    vhs._logger.setLevel(logging.DEBUG)


@pytest.fixture(scope="session")
def auth():
    if "VHS_TEST_GH_LOGIN" in os.environ and "VHS_TEST_GH_PASS" in os.environ:
        return github.Auth.Login(
            os.environ["VHS_TEST_GH_LOGIN"].strip(),
            os.environ["VHS_TEST_GH_PASS"].strip(),
        )


@pytest.mark.xfail(
    sys.platform != "darwin", reason="system VHS installation is broken there :("
)
def test_system_vhs(tmpdir, auth):
    system_vhs = shutil.which("vhs")
    assert system_vhs is not None, "vhs should be installed on your system to run tests"

    detected_vhs = vhs.resolve(cache_path=tmpdir, auth=auth)
    assert detected_vhs._vhs_path == pathlib.Path(system_vhs)

    _do_vhs_test(
        detected_vhs,
        tmpdir,
        system_vhs,
        shutil.which("ttyd"),
        shutil.which("ffmpeg"),
    )


@pytest.mark.linux
def test_system_vhs_unavailable(tmpdir, auth):
    detected_vhs = vhs.resolve(cache_path=tmpdir, env={"PATH": os.defpath}, auth=auth)
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
def test_system_vhs_unavailable_fail(tmpdir, auth):
    with pytest.raises(vhs.VhsError, match=r"VHS is not installed on your system"):
        vhs.resolve(cache_path=tmpdir, env={"PATH": os.defpath}, auth=auth)


@pytest.mark.linux
@pytest.mark.darwin
@pytest.mark.win32
def test_system_vhs_outdated_fail(tmpdir, auth):
    with pytest.raises(vhs.VhsError, match=r"version 9999.0.0 or newer"):
        vhs.resolve(cache_path=tmpdir, min_version="9999.0.0", auth=auth)


def _do_vhs_test(
    detected_vhs: vhs.Vhs,
    tmpdir,
    vhs_path,
    ttyd_path,
    ffmpeg_path,
):
    which = "where" if sys.platform == "win32" else "which"

    res = _run_inline(
        detected_vhs,
        f"""
        Type "{which} vhs"
        Enter
        Sleep 500ms
        Type "{which} ttyd"
        Enter
        Sleep 500ms
        Type "{which} ffmpeg"
        Enter
        Sleep 500ms
        """,
        tmpdir,
    )

    assert _path_in_res(vhs_path, res)
    assert _path_in_res(ttyd_path, res)
    assert _path_in_res(ffmpeg_path, res)


def _path_in_res(s, res) -> bool:
    s, res = str(s), str(res)
    if sys.platform == "win32":
        s, res = s.lower(), res.lower()
    return s in res.replace("\n", "").replace("\r", "")


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
def test_env(tmpdir, runner, auth):
    var_name = "%SOME_VAR%" if sys.platform == "win32" else "$SOME_VAR"
    res = runner(
        vhs.resolve(
            cache_path=tmpdir, env={**os.environ, "SOME_VAR": "SOME_TEXT"}, auth=auth
        ),
        f"""
        Type "echo {var_name}"
        Enter
        Sleep 500ms
        """,
        tmpdir,
    )

    assert "SOME_TEXT" in res

    var_name_1 = "%SOME_VAR_1%" if sys.platform == "win32" else "$SOME_VAR_1"
    var_name_2 = "%SOME_VAR_2%" if sys.platform == "win32" else "$SOME_VAR_2"
    res = runner(
        vhs.resolve(
            cache_path=tmpdir, env={**os.environ, "SOME_VAR_1": "SOME_TEXT"}, auth=auth
        ),
        f"""
        Type "echo {var_name_1}"
        Enter
        Sleep 500ms
        Type "echo {var_name_2}"
        Enter
        Sleep 500ms
        """,
        tmpdir,
        env={**os.environ, "SOME_VAR_2": "OTHER_TEXT"},
    )

    assert "SOME_TEXT" not in res
    assert "OTHER_TEXT" in res


@pytest.mark.parametrize("runner", [_run, _run_inline])
def test_cwd(tmpdir, runner, auth):
    pwd = "cd" if sys.platform == "win32" else "pwd"

    cwd1 = tmpdir / "cwd1"
    cwd1.mkdir()

    res = runner(
        vhs.resolve(cache_path=tmpdir, cwd=cwd1, auth=auth),
        f"""
        Type "{pwd}"
        Enter
        Sleep 500ms
        """,
        tmpdir,
    )

    assert _path_in_res(cwd1, res)

    cwd2 = tmpdir / "cwd2"
    cwd2.mkdir()

    res = runner(
        vhs.resolve(cache_path=tmpdir, cwd=cwd1, auth=auth),
        f"""
        Type "{pwd}"
        Enter
        Sleep 500ms
        """,
        tmpdir,
        cwd=cwd2,
    )

    assert not _path_in_res(cwd1, res)
    assert _path_in_res(cwd2, res)


@pytest.mark.linux
def test_progress(tmpdir, capsys, auth):
    vhs.resolve(
        cache_path=tmpdir,
        env={"PATH": os.defpath},
        reporter=vhs.DefaultProgressReporter(),
        auth=auth,
    )

    err: str = capsys.readouterr().err

    assert "resolving ffmpeg" in err
    assert "downloading ffmpeg" in err
    assert "processing ffmpeg" in err
    assert "resolving ttyd" in err
    assert "downloading ttyd" in err
    assert "processing ttyd" in err
    assert "resolving vhs" in err
    assert "downloading vhs" in err
    assert "processing vhs" in err
    assert err.endswith("\n")
