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
        if script.name == "xdobia15_get_urls.py":
            continue
            #command.append("--chromium")
        #############################################

        result = subprocess.run(
            command,
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
        if result.stderr:
            print(f"=== {script.name} errors ===", file=sys.stderr)
            print(result.stderr, file=sys.stderr, end="")
        if result.returncode != 0:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
