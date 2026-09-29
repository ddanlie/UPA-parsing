from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    scripts = sorted(SCRIPT_DIR.glob("*_get_urls.py"))
    failed = False

    for script in scripts:
        command = [sys.executable, str(script)]

        #############################################
        if script.name == "xdobia15_get_urls.py" or script.name == "xblaze38_get_urls.py":
            continue
            #command.append("--chromium")
        #############################################

        process = subprocess.Popen(
            command,
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            text=True,
        )
        if process.stdout is None:
            print(f"Failed to capture stdout for {script.name}", file=sys.stderr)
            failed = True
            continue
        for line in process.stdout:
            print(line, end="", flush=True)
        returncode = process.wait()
        stderr = process.stderr
        if stderr:
            print(f"=== {script.name} errors ===", file=sys.stderr)
            print(stderr.read() , file=sys.stderr, end="")
        if returncode != 0:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
