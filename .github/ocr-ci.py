"""Read-only upstream OCR CI: trusted base, immutable range, count-only output."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 1_000_000
spec = importlib.util.spec_from_file_location(
    "ocr_evidence", ROOT / ".github/security-review/preflight.py")
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def require(condition):
    if not condition:
        raise ValueError("invalid-ci-input")


def configuration():
    require(all(os.environ.get(name) for name in (
        "OCR_LLM_URL", "OCR_LLM_TOKEN", "OCR_LLM_MODEL", "OCR_LLM_PROTOCOL")))
    endpoint = urlsplit(os.environ["OCR_LLM_URL"])
    require(endpoint.scheme == "https" and endpoint.hostname and not endpoint.username
            and not endpoint.password and not endpoint.fragment and not endpoint.query)
    endpoint.port
    require(os.environ["OCR_LLM_PROTOCOL"] in ("openai", "openai-responses", "anthropic"))


def sha(value):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{40}", value))
    return value


def git(*args, **kwargs):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, timeout=60,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **kwargs).stdout


def fetch():
    number = os.environ["PR_NUMBER"]
    require(re.fullmatch("[1-9][0-9]*", number))
    base, head = sha(os.environ["BASE_SHA"]), sha(os.environ["HEAD_SHA"])
    token = os.environ["GH_TOKEN"]
    require(token)
    encoded = base64.b64encode(("x-access-token:" + token).encode()).decode()
    git("-c", "credential.helper=", "-c",
        "http.https://github.com/.extraheader=AUTHORIZATION: basic " + encoded,
        "fetch", "--no-tags", "origin", "pull/" + number + "/head")
    require(git("rev-parse", "FETCH_HEAD").decode().strip() == head)
    merge_base = sha(git("merge-base", base, head).decode().strip())
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write("merge_base=" + merge_base + "\n")


def file_limit():
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))


def run(command, environment, stdout, stderr):
    with subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout,
                          stderr=stderr, start_new_session=True,
                          preexec_fn=file_limit) as child:
        try:
            return child.wait(timeout=180)
        finally:
            # Only this owned process group; no target processes or shared services.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()


def summary(document, base, head, exit_code):
    require(isinstance(document, dict))
    comments = document.get("comments")
    require(isinstance(comments, list) and len(comments) <= 10000
            and all(isinstance(item, dict) for item in comments))
    evidence.check_ocr(document, base, head, exit_code)
    coverage = document["manifest"]["coverage"]
    return {"status": "complete", "selected": len(coverage["selected"]),
            "completed": len(coverage["completed"]), "reused": len(coverage["reused"]),
            "findings": len(comments), "details_published": False}


def review():
    configuration()
    base, head = sha(os.environ["BASE_SHA"]), sha(os.environ["HEAD_SHA"])
    binary = Path(os.environ["RUNNER_TEMP"]) / "ocr-cli/node_modules/.bin/ocr"
    with tempfile.TemporaryDirectory(prefix="ocr-private-", dir=os.environ["RUNNER_TEMP"]) as scratch:
        environment = {"PATH": os.environ["PATH"], "HOME": scratch, "TMPDIR": scratch,
                       "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
                       "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
                       "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
                       "OCR_NO_UPDATE": "1"}
        environment.update({name: os.environ[name] for name in (
            "OCR_LLM_URL", "OCR_LLM_TOKEN", "OCR_LLM_MODEL", "OCR_LLM_PROTOCOL")})
        home = Path(scratch) / ".opencodereview"
        home.mkdir(mode=0o700)
        config = {"llm": {
            "url": environment["OCR_LLM_URL"], "model": environment["OCR_LLM_MODEL"],
            "protocol": environment["OCR_LLM_PROTOCOL"],
            "auth_token_cmd": 'printf "%s" "$OCR_LLM_TOKEN"',
            "extra_body": {} if environment["OCR_LLM_PROTOCOL"] == "anthropic"
            else {"store": False}}}
        with open(home / "config.json", "x",
                  opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            json.dump(config, stream)
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            code = run([str(binary), "review", "--from", base, "--to", head,
                        "--format", "json", "--audience", "agent", "--concurrency", "1",
                        "--effort", "low", "--max-tokens-budget", "20000", "--timeout", "2"],
                       environment, output, errors)
            output.seek(0)
            raw = output.read(LIMIT + 1)
            require(len(raw) <= LIMIT)
            result = summary(json.loads(raw, object_pairs_hook=evidence.unique), base, head, code)
            print(json.dumps(result, sort_keys=True))
            path = os.environ.get("GITHUB_STEP_SUMMARY")
            if path:
                with open(path, "a") as stream:
                    stream.write("OCR complete for the selected range: "
                                 f"{result['completed']} completed, {result['reused']} reused, "
                                 f"{result['findings']} findings. Details were not published.\n")


def main():
    stage = sys.argv[1] if len(sys.argv) == 2 else ""
    if stage not in ("validate", "fetch", "review"):
        print("::error::Invalid OCR CI operation; no review performed.")
        return 1
    try:
        if stage == "validate":
            configuration()
            version = git("--version").decode()
            match = re.match(r"git version (\d+)\.(\d+)", version)
            require(match and tuple(map(int, match.groups())) >= (2, 41))
            print("OCR prerequisites passed; this is not review evidence.")
        elif stage == "fetch":
            fetch()
        else:
            review()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError):
        print("::error::OCR CI " + stage + " failed or produced incomplete evidence. "
              "Raw output was withheld; no complete review is claimed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
