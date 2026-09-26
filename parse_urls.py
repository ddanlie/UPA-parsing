from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
URLS_PER_SCRIPT_RUN = 4

scripts = sorted(SCRIPT_DIR.glob("*_parse_urls.py"))
script_to_run_index = 0

def _run_scrtipt(urls_script_input: list[str]):
    global scripts, script_to_run_index
    
    script = scripts[script_to_run_index]

    #############################################
    if script.name == "xdobia15_parse_urls.py":
        script_to_run_index = (script_to_run_index + 1) % len(scripts)
        script = scripts[script_to_run_index]
    #############################################

    script_to_run_index = (script_to_run_index + 1) % len(scripts)
    command = [sys.executable, str(script)]
    result = subprocess.run(
        command,
        cwd=SCRIPT_DIR,
        input="\n".join(urls_script_input),
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(f"=== {script.name} errors ===", file=sys.stderr)
        print(result.stderr, file=sys.stderr, end="")

    return result.returncode


def main():
    failed = False
    urls_script_input = []
    for url in sys.stdin:
        urls_script_input.insert(0, url) # respect the input order
        if len(urls_script_input) % URLS_PER_SCRIPT_RUN == 0:
            if _run_scrtipt(urls_script_input) != 0:
                failed = True
            urls_script_input.clear()
    
    if urls_script_input:
        if _run_scrtipt(urls_script_input) != 0:
            failed = True
        urls_script_input.clear()

    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
