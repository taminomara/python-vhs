"""A package that includes VHS binary, and a simple API to run it."""

import os
import pathlib
import signal
import subprocess
import typing as _t

import _version

__version__ = _version.__version__
__version_tuple__ = _version.__version_tuple__

__all__ = [
    'VhsError',
    'bin_path',
    'vhs',
    'vhs_inline',
]


class VhsError(subprocess.CalledProcessError):
    """
    Thrown when VHS process fails.

    """

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                returncode = f'signal {signal.Signals(-self.returncode)}'
            except ValueError:
                returncode = f'unknown signal {self.returncode}'
        else:
            returncode = f'code {self.returncode}'

        msg = f'VHS run failed with {returncode}'
        if self.stderr:
            msg += '\n\nStderr:\n' + self.stderr
        if self.stdout:
            msg += '\n\nStdout:\n' + self.stdout
        return msg


def bin_path() -> pathlib.Path:
    """
    Return path to the folder with VHS executable and its dependencies.

    """

    return pathlib.Path(__file__).parent / 'bin'


def vhs(
    input_path: os.PathLike,
    output_path: _t.Optional[os.PathLike] = None,
    *,
    quiet: bool = True,
    env: _t.Optional[_t.Dict[str, str]] = None,
    cwd: _t.Optional[os.PathLike] = None,
):
    """
    Renter the given VHS file.

    :param input_path:
        path to a tape file.
    :param output_path:
        path to the output file.
        By default, puts output to whichever path is set in the tape.
    :param quiet:
        catch any output from the VHS binary and add it
        to the :class:`VhsError` in case of failure.
        If set to `False`, VHS will print directly to stdout/stderr.
    :param env:
        overrides environment variables for the VHS process.
    :param cwd:
        overrides current working directory for the VHS process.
    :raises VhsError: VHS process failed with non-zero return code.

    """

    _run_impl(
        input_path=input_path,
        output_path=output_path,
        quiet=quiet,
        env=env,
        cwd=cwd,
    )


def vhs_inline(
    input_text: str,
    output_path: _t.Optional[os.PathLike] = None,
    *,
    quiet: bool = True,
    env: _t.Optional[_t.Dict[str, str]] = None,
    cwd: _t.Optional[os.PathLike] = None,
):
    """
    Like :func:`vhs`, but accepts tape contents rather than a file path.

    :param input_text:
        contents of a tape.
    :param output_path:
        path to the output file.
        By default, puts output to whichever path is set in the tape.
    :param quiet:
        catch any output from the VHS binary and add it
        to the :class:`VhsError` in case of failure.
        If set to `False`, VHS will print directly to stdout/stderr.
    :param env:
        overrides environment variables for the VHS process.
    :param cwd:
        overrides current working directory for the VHS process.
    :raises VhsError: VHS process failed with non-zero return code.

    """

    _run_impl(
        input_text=input_text,
        output_path=output_path,
        quiet=quiet,
        env=env,
        cwd=cwd,
    )


def _run_impl(
    input_path: _t.Optional[os.PathLike] = None,
    input_text: _t.Optional[str] = None,
    output_path: _t.Optional[os.PathLike] = None,
    quiet: bool = True,
    env: _t.Optional[_t.Dict[str, str]] = None,
    cwd: _t.Optional[os.PathLike] = None,
):
    vhs_bin_path = bin_path()

    assert (
        (vhs_bin_path / 'vhs').exists(),
        'broken python-vhs distribution, please fill an issue '
        'at https://github.com/taminomara/python-vhs/issues/new'
    )

    path = env.get('PATH') or os.environ.get('PATH') or ''
    path = str(vhs_bin_path) + ':' + path if path else str(vhs_bin_path)

    env = {**env, 'PATH': path}

    args = ['vhs']
    capture_output = False
    if quiet:
        args += ['-q']
        capture_output = True
    if output_path:
        args += ['-o', output_path]
    if input_path is not None:
        args += [input_path]

    try:
        subprocess.run(
            args,
            capture_output=capture_output,
            input=input_text,
            env=env,
            cwd=cwd,
            check=True,

        )
    except subprocess.CalledProcessError as e:
        raise VhsError(
            e.returncode,
            e.cmd,
            e.output,
            e.stderr,
        ) from None
