import re
import subprocess
import tempfile
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Problem, Submission, SubmissionResult, SubmissionStatus, TestCase, Verdict

LANGUAGES: dict[str, dict] = {
    "python": {
        "image": "kgmp/sandbox-python:1.0",
        "ext": "py",
        "run": ["python3", "/sandbox/main.py"],
    },
    "javascript": {
        "image": "kgmp/sandbox-node:1.0",
        "ext": "js",
        "run": ["node", "/sandbox/main.js"],
    },
}

TIME_LIMIT_EXCEEDED_RC = 124
OOM_KILL_RC = 137

MAX_CAPTURED_BYTES = 1_000_000
STORE_OUTPUT_CHARS = 10_000

BASE_DOCKER_FLAGS = [
    "--network", "none",
    "--read-only",
    "--tmpfs", "/tmp:size=64m",
]


def supported_languages() -> list[str]:
    return sorted(LANGUAGES.keys())


def _normalize_output(raw: str) -> str:
    # Remove all whitespace for comparison (handles [0, 1] vs [0,1])
    return "".join(raw.split())


def _outputs_match(actual: str, expected: str) -> bool:
    return _normalize_output(actual) == _normalize_output(expected)


def _truncate(text: str) -> str:
    return text[:STORE_OUTPUT_CHARS]


def _verdict_from_exit_code(rc: int) -> Verdict:
    if rc == TIME_LIMIT_EXCEEDED_RC:
        return Verdict.time_limit_exceeded
    if rc == OOM_KILL_RC:
        return Verdict.memory_limit_exceeded
    if rc != 0:
        return Verdict.runtime_error
    return Verdict.accepted


def _wrap_python_code(source_code: str) -> str:
    """Wrap Python code with I/O harness for LeetCode-style solutions."""
    harness = """
import sys
import ast
import re

def parse_input(input_str):
    '''Parse various input formats and extract parameters.'''
    # Try to detect common patterns
    input_str = input_str.strip()
    
    # Pattern 1: "nums = [1,2,3], target = 9" (Two Sum style)
    if '=' in input_str and '[' in input_str:
        # Use regex to extract variable assignments with proper bracket handling
        pattern = r'(\w+)\s*=\s*(\[.*?\]|[^,]+)(?:,\s*|$)'
        matches = re.findall(pattern, input_str)
        result = []
        for key, value in matches:
            value = value.strip()
            try:
                parsed = ast.literal_eval(value)
                result.append(parsed)
            except:
                result.append(value)
        return result
    
    # Pattern 2: JSON-like or space-separated values
    try:
        # Try parsing as JSON
        import json
        return json.loads(input_str)
    except:
        pass
    
    # Pattern 3: Space-separated numbers
    cleaned = input_str.replace(' ', '').replace('-', '').replace('.', '')
    if cleaned.isdigit():
        return [float(x) if '.' in x else int(x) for x in input_str.split()]
    
    # Pattern 4: Single value
    try:
        return int(input_str)
    except:
        try:
            return float(input_str)
        except:
            return input_str

# User's code below
"""
    return harness + source_code + """

# Main execution
if __name__ == "__main__":
    input_str = sys.stdin.read()
    parsed = parse_input(input_str)
    
    # Try to detect Solution class and call appropriate method
    solution_class = globals().get('Solution')
    if solution_class:
        import inspect
        if inspect.isclass(solution_class):
            solution = solution_class()
            # Find the main method (usually the first one that's not __init__)
            methods = [m for m in dir(solution) if not m.startswith('_') and callable(getattr(solution, m))]
            if methods:
                method_name = methods[0]
                method = getattr(solution, method_name)
                # Call with parsed arguments
                if isinstance(parsed, list):
                    result = method(*parsed)
                else:
                    result = method(parsed)
                print(result)
    else:
        # If no Solution class, try to execute the code directly
        # The code should handle its own I/O
        pass
"""


@dataclass
class CaseResult:
    test_case_id: int
    passed: bool
    verdict: Verdict
    actual_output: str
    exec_time_ms: int


def _run_command(config: dict) -> list[str]:
    inner = " ".join(config["run"])
    pipeline = f"{inner} 2>/dev/null | head -c {MAX_CAPTURED_BYTES}"
    return ["timeout", str(settings.time_limit_seconds), "/bin/sh", "-c", pipeline]


def _run_test_case(
    language: str,
    source_code: str,
    test_case: TestCase,
    container_name: str,
) -> CaseResult:
    config = LANGUAGES[language]
    filename = f"main.{config['ext']}"
    run_cmd = _run_command(config)
    started = time.perf_counter()

    # Wrap Python code with I/O harness
    if language == "python":
        source_code = _wrap_python_code(source_code)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        import os

        source_path = os.path.join(tmpdir, filename)
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            *BASE_DOCKER_FLAGS,
            "--memory", f"{settings.memory_limit_mb}m",
            "--cpus", str(settings.cpu_limit),
            "--pids-limit", str(settings.pids_limit),
            "-i",
            "-v", f"{tmpdir}:/sandbox:ro",
            config["image"],
            *run_cmd,
        ]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = proc.communicate(
                input=test_case.input.encode("utf-8"),
                timeout=settings.wall_timeout_seconds,
            )
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            return CaseResult(
                test_case_id=test_case.id,
                passed=False,
                verdict=Verdict.time_limit_exceeded,
                actual_output="",
                exec_time_ms=int((time.perf_counter() - started) * 1000),
            )

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    exec_time_ms = int((time.perf_counter() - started) * 1000)

    if rc != 0:
        verdict = _verdict_from_exit_code(rc)
        return CaseResult(
            test_case_id=test_case.id,
            passed=False,
            verdict=verdict,
            actual_output=_truncate(stdout),
            exec_time_ms=exec_time_ms,
        )

    passed = _outputs_match(stdout, test_case.expected_output)
    verdict = Verdict.accepted if passed else Verdict.wrong_answer
    return CaseResult(
        test_case_id=test_case.id,
        passed=passed,
        verdict=verdict,
        actual_output=_truncate(stdout),
        exec_time_ms=exec_time_ms,
    )


def _compute_verdict(results: list[CaseResult]) -> Verdict:
    first_fail = next((r.verdict for r in results if not r.passed), None)
    if first_fail is None:
        return Verdict.accepted
    if first_fail == Verdict.accepted:
        return Verdict.wrong_answer
    return first_fail


def grade_submission_sync(submission_id: int) -> None:
    db = SessionLocal()
    try:
        submission = db.get(Submission, submission_id)
        if submission is None:
            return

        submission.status = SubmissionStatus.running
        db.commit()

        test_cases = list(
            db.scalars(
                select(TestCase)
                .where(TestCase.problem_id == submission.problem_id)
                .order_by(TestCase.id)
            )
        )

        results: list[CaseResult] = []
        for test_case in test_cases:
            try:
                result = _run_test_case(
                    submission.language,
                    submission.source_code,
                    test_case,
                    container_name=f"codejudge-sandbox-{submission.id}-{test_case.id}",
                )
            except Exception:
                result = CaseResult(
                    test_case_id=test_case.id,
                    passed=False,
                    verdict=Verdict.runtime_error,
                    actual_output="",
                    exec_time_ms=0,
                )
            results.append(result)

            db.add(
                SubmissionResult(
                    submission_id=submission.id,
                    test_case_id=test_case.id,
                    passed=result.passed,
                    verdict=result.verdict,
                    actual_output=result.actual_output,
                    exec_time_ms=result.exec_time_ms,
                )
            )
        db.flush()

        total_weight = sum(tc.weight for tc in test_cases)
        passed_weight = sum(
            tc.weight for tc, r in zip(test_cases, results) if r.passed
        )
        submission.score = round(passed_weight / total_weight * 100, 2) if total_weight else 0.0
        submission.verdict = _compute_verdict(results)
        submission.status = SubmissionStatus.graded
        db.commit()
    except Exception:
        db.rollback()
        submission = db.get(Submission, submission_id)
        if submission is not None:
            submission.status = SubmissionStatus.failed
            db.commit()
        raise
    finally:
        db.close()
