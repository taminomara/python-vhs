"""A package that includes VHS binary, and a simple API to run it."""

import logging
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import typing as _t

logger = logging.getLogger('vhs')

try:
    from vhs._version import __version__, __version_tuple__
except ImportError:
    raise ImportError('vhs._version not found. if you are developing locally, '
                      'run `pip install --editable .[test,doc]` to generate it')

__all__ = [
    'VhsError',
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
        stderr = self.stderr
        if self.stderr:
            if isinstance(stderr, bytes):
                stderr = stderr.decode('utf-8', errors='replace')
            msg += f'\n\nStderr:\n{stderr}'
        stdout = self.stdout
        if self.stdout:
            if isinstance(stdout, bytes):
                stdout = stdout.decode('utf-8', errors='replace')
            msg += f'\n\nStdout:\n{stdout}'
        return msg


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

    base_path = pathlib.Path(__file__).parent
    bin_path = base_path / 'bin'
    lib_path = base_path / 'lib'

    if env is None:
        env = os.environ
    env = env.copy()

    env_bin_path = env.get('PATH') or os.environ.get('PATH') or ''
    env['PATH'] = str(bin_path) + ':' + env_bin_path if env_bin_path else str(bin_path)

    if sys.platform == 'darwin':
        env_lib_path = env.get('DYLD_LIBRARY_PATH') or os.environ.get('DYLD_LIBRARY_PATH') or ''
        env['DYLD_LIBRARY_PATH'] = str(lib_path) + ':' + env_lib_path if env_lib_path else str(lib_path)

    args = ['vhs']
    capture_output = False
    if quiet:
        args += ['-q']
        capture_output = True
    if output_path:
        args += ['-o', output_path]
    args += [input_path]

    try:
        logger.debug('running VHS with args %r', args)
        subprocess.run(
            args,
            capture_output=capture_output,
            env=env,
            cwd=cwd,
            check=True,
            shell=True,
        )
    except subprocess.CalledProcessError as e:
        raise VhsError(
            e.returncode,
            e.cmd,
            e.output,
            e.stderr,
        ) from None


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

    tmp_dir = pathlib.Path(tempfile.mkdtemp())
    try:
        input_path = tmp_dir / 'input.tape'
        input_path.write_text(input_text, 'utf-8')
        vhs(
            input_path=input_path,
            output_path=output_path,
            quiet=quiet,
            env=env,
            cwd=cwd,
        )
    finally:
        shutil.rmtree(tmp_dir)
