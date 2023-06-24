"""A package that includes VHS binary, and a simple API to run it."""

import logging
import os
import pathlib
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import typing as _t
import urllib.request

import github
import urllib3

_logger = logging.getLogger("vhs")

try:
    from vhs._version import __version__, __version_tuple__
except ImportError:
    raise ImportError(
        "vhs._version not found. if you are developing locally, "
        "run `pip install -e .[test,doc]` to generate it"
    )


__all__ = [
    "VhsError",
    "VhsRunError",
    "Vhs",
]


_PathLike = _t.Union[str, os.PathLike]


class VhsError(Exception):
    """
    Raised when VHS is unavailable, or when installation fails.

    """


class VhsRunError(VhsError, subprocess.CalledProcessError):
    """
    Raised when VHS process fails.

    """

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                returncode = f"signal {signal.Signals(-self.returncode)}"
            except ValueError:
                returncode = f"unknown signal {self.returncode}"
        else:
            returncode = f"code {self.returncode}"

        msg = f"VHS run failed with {returncode}"
        stderr = self.stderr
        if self.stderr:
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            msg += f"\n\nStderr:\n{stderr}"
        stdout = self.stdout
        if self.stdout:
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            msg += f"\n\nStdout:\n{stdout}"
        return msg


@_t.final
class Vhs:
    """
    Interface for a VHS installation.

    """

    # Do not call this, use `Vhs.resolve_or_install` instead.
    def __init__(
        self,
        *,
        _vhs_path: pathlib.Path,
        _path: str,
        _quiet: bool = True,
        _env: _t.Optional[_t.Dict[str, str]] = None,
        _cwd: _t.Optional[_PathLike] = None,
    ):
        self._vhs_path = _vhs_path
        self._path = _path
        self._quiet = _quiet
        self._env = _env
        self._cwd = _cwd

    def run(
        self,
        input_path: _PathLike,
        output_path: _t.Optional[_PathLike] = None,
        *,
        quiet: _t.Optional[bool] = True,
        env: _t.Optional[_t.Dict[str, str]] = None,
        cwd: _t.Optional[_PathLike] = None,
    ):
        """
        Renter the given VHS file.

        :param input_path:
            path to a tape file.
        :param output_path:
            path to the output file.
            By default, puts output to whichever path is set in the tape.
        :param quiet:
            redefine :attr:`Vhs.quiet` for this invocation.
        :param env:
            redefine :attr:`Vhs.env` for this invocation.
        :param cwd:
            redefine :attr:`Vhs.cmd` for this invocation.

        :raises VhsRunError: VHS process failed with non-zero return code.

        """

        if quiet is None:
            quiet = self._quiet

        if env is None:
            env = self._env
        if env is None:
            env = os.environ.copy()
        else:
            env = env.copy()
        env["PATH"] = self._path

        if cwd is None:
            cwd = self._cwd

        args: _t.List[_t.Union[str, _PathLike]] = [self._vhs_path]
        capture_output = False
        if quiet:
            args += ["-q"]
            capture_output = True
        if output_path:
            args += ["-o", output_path]
        args += [input_path]

        try:
            _logger.debug("running VHS with args %r", args)
            subprocess.run(
                args,
                capture_output=capture_output,
                env=env,
                cwd=cwd,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise VhsRunError(
                e.returncode,
                e.cmd,
                e.output,
                e.stderr,
            ) from None

    def run_inline(
        self,
        input_text: str,
        output_path: _t.Optional[_PathLike] = None,
        *,
        quiet: _t.Optional[bool] = True,
        env: _t.Optional[_t.Dict[str, str]] = None,
        cwd: _t.Optional[_PathLike] = None,
    ):
        """
        Like :meth:`~Vhs.run`, but accepts tape contents rather than a file.

        :param input_text:
            contents of a tape.
        :param output_path:
            path to the output file.
            By default, puts output to whichever path is set in the tape.
        :param quiet:
            redefine :attr:`Vhs.quiet` for this invocation
        :param env:
            redefine :attr:`Vhs.env` for this invocation
        :param cwd:
            redefine :attr:`Vhs.cmd` for this invocation

        :raises VhsRunError: VHS process failed with non-zero return code.

        """

        with tempfile.TemporaryDirectory() as d:
            tmp_file = pathlib.Path(d) / "input.tape"
            tmp_file.write_text(input_text)
            self.run(
                input_path=tmp_file,
                output_path=output_path,
                quiet=quiet,
                env=env,
                cwd=cwd,
            )


def resolve(
    *,
    cache_path: _t.Optional[pathlib.Path] = None,
    min_version: str = "0.5.0",
    quiet: bool = True,
    env: _t.Optional[_t.Dict[str, str]] = None,
    cwd: _t.Optional[_PathLike] = None,
    install: bool = True,
    reporter: _t.Optional[_t.Callable[[str, int, int], None]] = None,
) -> "Vhs":
    """
    Find a system VHS installation or download VHS from GitHub.

    If VHS is not installed, or it's outdated, try to download it
    and install it into `cache_path`.

    Automatic download only works on 64-bit Linux and Windows.
    MacOS users will be presented with an instruction to use `brew`,
    and other systems users will get a link to VHS installation guide.

    :param cache_path:
        path where VHS binaries should be downloaded to.
    :param min_version:
        minimal VHS version required.
    :param quiet:
        if true (default), any output from the VHS binary is hidden.
    :param env:
        overrides environment variables for the VHS process.
    :param cwd:
        overrides current working directory for the VHS process.
    :param install:
        if false, disables installing VHS from GitHub.
    :param reporter:
        a hook that will be called to inform user about installation
        progress. The hook should accept three parameters: a description
        of a currently performed operation, number of bytes downloaded,
        total number of bytes to download.
        See :func:`default_stderr_reporter` for an example.
    :return:
        resolved VHS installation.
    :raises VhsError:
        VHS not available or installation failed.

    """

    if cache_path is None:
        cache_path = pathlib.Path(tempfile.gettempdir()) / "python_vhs_cache"
    else:
        cache_path = pathlib.Path(cache_path)

    vhs_path, path = _check_and_install(
        min_version, cache_path, _get_path(env), install, reporter
    )

    return Vhs(
        _vhs_path=vhs_path,
        _path=path,
        _quiet=quiet,
        _env=env,
        _cwd=cwd,
    )


def default_stderr_reporter(desc: str, dl_size: int, total_size: int, /):
    """
    Default progress reported that prints current progress to stderr.

    :param desc:
        description of the currently performed operation.
    :param dl_size:
        when the installer downloads files, this number indicates
        number of bytes downloaded so far. Otherwise, it is set to zero.
    :param total_size:
        when the installer downloads files, this number indicates
        total number of bytes to download. Otherwise, it is set to zero.

    """

    if total_size:
        print(
            f"{desc}: {dl_size}/{total_size}MB", file=sys.stderr, end="\r", flush=True
        )
    else:
        print(f"{desc}", file=sys.stderr)


def _get_path(env: _t.Optional[_t.Dict[str, str]]) -> str:
    path = (env or {}).get("PATH", None)
    if path is None:
        path = os.environ.get("PATH", None)
    if path is None and sys.platform != "win32":
        try:
            path = os.confstr("CS_PATH")
        except (AttributeError, ValueError):
            pass
    if path is None:
        path = os.defpath
    if path is None:
        path = ""
    return path


def _get_name(name: str):
    if sys.platform == "win32":
        return name + ".exe"
    else:
        return name


def _download_latest_release(
    api: github.Github,
    name: str,
    repo_name: str,
    dest: pathlib.Path,
    filter: _t.Callable[[str], bool],
    reporter: _t.Optional[_t.Callable[[str, int, int], None]],
):
    repo = api.get_repo(repo_name)

    for release in repo.get_releases():
        if release.draft or release.prerelease:
            continue

        for asset in release.assets:
            if filter(asset.name):
                browser_download_url = asset.browser_download_url
                break
        else:
            raise VhsError(f"unable to find {name} release for platform {sys.platform}")

        break
    else:
        raise VhsError(f"unable to find latest {name} release")

    if reporter is not None:
        reporthook = lambda bn, bs, sz: reporter(f"downloading {name}", bn * bs, sz)
    else:
        reporthook = None

    basename = browser_download_url.rstrip("/").rsplit("/", maxsplit=1)[1]
    urllib.request.urlretrieve(
        browser_download_url, dest / basename, reporthook=reporthook
    )
    return dest / basename


def _install_vhs(
    api: github.Github,
    bin_path: pathlib.Path,
    reporter: _t.Optional[_t.Callable[[str, int, int], None]],
):
    if sys.platform == "linux":
        filter = lambda name: name == "vhs_Linux_x86_64.tar.gz"
    elif sys.platform == "win32":
        filter = lambda name: name == "vhs_Windows_x86_64.zip"
    else:
        raise VhsError(f"platform {sys.platform} is not supported")

    with tempfile.TemporaryDirectory() as tmp_dir_s:
        tmp_dir = pathlib.Path(tmp_dir_s)

        try:
            tmp_file = _download_latest_release(
                api, "vhs", "charmbracelet/vhs", tmp_dir, filter, reporter
            )

            shutil.unpack_archive(tmp_file, tmp_dir)
            vhs_file = bin_path / _get_name("vhs")
            os.replace(tmp_dir / _get_name("vhs"), vhs_file)
            if sys.platform != "win32":
                vhs_file.chmod(vhs_file.stat().st_mode | stat.S_IEXEC)
        except Exception as e:
            raise VhsError(f"vhs install failed: {e}")


def _install_ttyd(
    api: github.Github,
    bin_path: pathlib.Path,
    reporter: _t.Optional[_t.Callable[[str, int, int], None]],
):
    if sys.platform == "linux":
        filter = lambda name: name.endswith("x86_64")
    elif sys.platform == "win32":
        filter = lambda name: name.endswith(("win10.exe", "win32.exe"))
    else:
        raise VhsError(f"platform {sys.platform} is not supported")

    with tempfile.TemporaryDirectory() as tmp_dir_s:
        tmp_dir = pathlib.Path(tmp_dir_s)

        try:
            tmp_file = _download_latest_release(
                api, "ttyd", "tsl0922/ttyd", tmp_dir, filter, reporter
            )
            ttyd_file = bin_path / _get_name("ttyd")
            os.replace(tmp_file, ttyd_file)
            if sys.platform != "win32":
                ttyd_file.chmod(ttyd_file.stat().st_mode | stat.S_IEXEC)
        except Exception as e:
            raise VhsError(f"ttyd install failed: {e}")


def _install_ffmpeg(
    api: github.Github,
    bin_path: pathlib.Path,
    reporter: _t.Optional[_t.Callable[[str, int, int], None]],
):
    if sys.platform == "linux":
        filter = (
            lambda name: name.startswith("ffmpeg-n5.1") and "linux64-gpl-5.1" in name
        )
    elif sys.platform == "win32":
        filter = lambda name: name.startswith("ffmpeg-n5.1") and "win64-gpl-5.1" in name
    else:
        raise VhsError(f"platform {sys.platform} is not supported")

    with tempfile.TemporaryDirectory() as tmp_dir_s:
        tmp_dir = pathlib.Path(tmp_dir_s)

        try:
            tmp_file = _download_latest_release(
                api, "ffmpeg", "BtbN/FFmpeg-Builds", tmp_dir, filter, reporter
            )

            archive_basename = tmp_file.name
            if archive_basename.endswith(".zip"):
                archive_basename = archive_basename[: -len(".zip")]
            elif archive_basename.endswith(".tar.gz"):
                archive_basename = archive_basename[: -len(".tar.gz")]
            elif archive_basename.endswith(".tar.xz"):
                archive_basename = archive_basename[: -len(".tar.xz")]

            shutil.unpack_archive(tmp_file, tmp_dir)

            for file in (tmp_dir / archive_basename / "bin").iterdir():
                dst_file = bin_path / file.name
                os.replace(file, dst_file)
                if sys.platform != "win32":
                    dst_file.chmod(dst_file.stat().st_mode | stat.S_IEXEC)

        except Exception as e:
            raise VhsError(f"ffmpeg install failed: {e}")


def _check_version(
    version: str, vhs_path: _PathLike
) -> _t.Tuple[bool, _t.Optional[str]]:
    version_tuple = tuple(int(c) for c in version.split("."))
    try:
        system_version_text_b = subprocess.check_output([vhs_path, "--version"])
        system_version_text = system_version_text_b.decode().strip()
        if match := re.search(r"(\d+\.\d+\.\d+)", system_version_text):
            system_version = match.group(1)
            system_version_tuple = tuple(int(c) for c in system_version.split("."))
            if system_version_tuple >= version_tuple:
                return True, system_version
            else:
                _logger.debug(
                    "%s is outdated (got %s, required %s)",
                    vhs_path,
                    system_version,
                    version,
                )
                return False, system_version
        else:
            _logger.debug(
                "%s printed invalid version %r", vhs_path, system_version_text
            )
    except (subprocess.SubprocessError, OSError, UnicodeDecodeError):
        _logger.debug("%s failed to print its version", vhs_path, exc_info=True)

    return False, None


def _check_and_install(
    version: str,
    bin_path: pathlib.Path,
    path: str,
    install: bool,
    reporter: _t.Optional[_t.Callable[[str, int, int], None]] = None,
) -> _t.Tuple[pathlib.Path, str]:
    if version.startswith("v"):
        version = version[1:]

    # Try finding pre-installed vhs.
    system_vhs_path = shutil.which("vhs", path=path)
    system_version = None
    if system_vhs_path:
        can_use_system_vhs, system_version = _check_version(version, system_vhs_path)
        if can_use_system_vhs:
            _logger.debug("using pre-installed vhs at %s", system_vhs_path)
            return pathlib.Path(system_vhs_path), path
    else:
        _logger.debug("pre-installed vhs not found")

    # Check system compatibility.
    if sys.platform == "darwin":
        if system_vhs_path:
            raise VhsError(
                f"you have VHS {system_version}, "
                f"but version {version} or newer is required; "
                f"run `brew upgrade vhs` to upgrade it, or see installation instructions "
                f"at https://github.com/charmbracelet/vhs#installation"
            )
        else:
            raise VhsError(
                f"VHS is not installed on your system; "
                f"run `brew install vhs` to install it, or see installation instructions "
                f"at https://github.com/charmbracelet/vhs#installation"
            )
    elif (
        not install
        or sys.platform not in ["win32", "linux"]
        or platform.architecture()[0] != "64bit"
    ):
        if system_vhs_path:
            raise VhsError(
                f"you have VHS {system_version}, "
                f"but version {version} or newer is required; "
                f"see upgrade instructions "
                f"at https://github.com/charmbracelet/vhs#installation"
            )
        else:
            raise VhsError(
                f"VHS is not installed on your system; "
                f"see installation instructions "
                f"at https://github.com/charmbracelet/vhs#installation"
            )

    # Download binary releases or use cached ones.
    api = github.Github(retry=urllib3.Retry(10, backoff_factor=0.2, backoff_jitter=1))

    if not bin_path.joinpath(_get_name("ttyd")).exists():
        _logger.debug("downloading ttyd")
        _install_ttyd(api, bin_path, reporter)
    else:
        _logger.debug("using cached ttyd")

    if not bin_path.joinpath(_get_name("ffmpeg")).exists():
        _logger.debug("downloading ffmpeg")
        _install_ffmpeg(api, bin_path, reporter)
    else:
        _logger.debug("using cached ffmpeg")

    if path:
        sep = ";" if sys.platform == "win32" else ":"
        path = str(bin_path) + sep + path
    else:
        path = str(bin_path)

    vhs_path = bin_path / _get_name("vhs")
    if vhs_path.exists():
        can_use_cached_vhs, _ = _check_version(version, vhs_path)
        if can_use_cached_vhs:
            _logger.debug("using cached vhs")
            return vhs_path, path

    _install_vhs(api, bin_path, reporter)

    can_use_cached_vhs, _ = _check_version(version, vhs_path)
    if not can_use_cached_vhs:
        _logger.warning(
            "downloaded latest vhs is outdated; "
            "are you sure min_vhs_version is correct?"
        )

    return vhs_path, path
