import subprocess
from typing import Tuple


def run_subprocess(command: str, args: list = None, timeout: int = 60) -> Tuple[str, str, int]:
    """
    Run a subprocess command and return stdout, stderr, and exit code.
    """
    if args is None:
        args = []
    try:
        process = subprocess.Popen(
            [command] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(timeout=timeout)
        return stdout.strip(), stderr.strip(), process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        return "", f"Command '{command}' timed out after {timeout} seconds", -1
    except Exception as e:
        return "", str(e), -1
