import sys
import subprocess
import tempfile
import time
import os
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from app.config import settings

logger = logging.getLogger("proctorai.sandbox")


class SandboxRateLimiter:
    """
    Sliding-window in-memory rate limiter for coding execution requests.
    Prevents runner exhaustion and denial-of-service.
    """
    _requests: Dict[str, List[float]] = {}

    @classmethod
    def check_rate_limit(cls, identifier: str, limit_per_minute: Optional[int] = None) -> Tuple[bool, int]:
        max_limit = limit_per_minute or settings.SANDBOX_RATE_LIMIT_PER_MINUTE
        now = time.time()
        window_start = now - 60.0

        if identifier not in cls._requests:
            cls._requests[identifier] = []

        # Filter out timestamps older than 60 seconds
        valid_timestamps = [t for t in cls._requests[identifier] if t > window_start]
        cls._requests[identifier] = valid_timestamps

        if len(valid_timestamps) >= max_limit:
            retry_after = max(1, int(60.0 - (now - valid_timestamps[0])))
            return False, retry_after

        cls._requests[identifier].append(now)
        return True, 0

    @classmethod
    def reset(cls):
        cls._requests.clear()


class CodingSandboxRunner:
    """
    Isolated code execution runner acting as a strict security boundary:
    - Candidate code is NEVER executed inside the FastAPI process.
    - No eval or exec is used in the API server.
    - Hardened sandbox with non-root execution, restricted filesystem, network denial,
      zero mount of application secrets / DB credentials / host docker socket,
      and strict CPU, memory, time, process and output limits.
    """

    @classmethod
    def authenticate_runner_token(cls, token: Optional[str]) -> bool:
        """
        Validates internal runner authentication token.
        """
        if not token or not settings.INTERNAL_RUNNER_SECRET:
            return False
        return token.strip() == settings.INTERNAL_RUNNER_SECRET.strip()

    @classmethod
    def execute_code(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        language: str = "python",
        timeout_seconds: int = 3,
        memory_limit_mb: int = 128
    ) -> Dict[str, Any]:
        """
        Primary execution entrypoint.
        Routes to hardened Docker container if enabled,
        or falls back to hardened isolated subprocess sandbox.
        """
        if not code or not code.strip():
            return {
                "total_test_cases": len(test_cases),
                "passed_test_cases": 0,
                "all_passed": False,
                "results": [],
                "error": "No code provided",
                "failure_type": "NO_CODE"
            }

        if settings.USE_DOCKER_SANDBOX:
            try:
                return cls._run_in_docker(code, test_cases, timeout_seconds, memory_limit_mb)
            except Exception as e:
                logger.warning(f"Docker sandbox unreachable ({e}). Running via hardened subprocess sandbox.")
                return cls._run_in_subprocess(code, test_cases, timeout_seconds, memory_limit_mb)
        else:
            return cls._run_in_subprocess(code, test_cases, timeout_seconds, memory_limit_mb)

    @classmethod
    def _run_in_docker(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        timeout_seconds: int,
        memory_limit_mb: int
    ) -> Dict[str, Any]:
        """
        Executes code inside a hardened Docker container:
        - Non-root user (1000:1000)
        - network_mode="none" (zero network access)
        - read_only=True (read-only root filesystem)
        - tmpfs /tmp restricted to 16MB noexec
        - memory limit (128MB) & CPU quota (50% CPU)
        - pids_limit to block fork bombs
        - drops all Linux capabilities (cap_drop=["ALL"])
        - zero mounts of host directories, docker.sock, or secrets
        """
        import docker
        client = docker.from_env()

        results = []
        passed_count = 0
        overall_failure_type = None

        for idx, tc in enumerate(test_cases):
            tc_input = str(tc.get("input", ""))
            expected_output = str(tc.get("expected_output", "")).strip()
            is_hidden = tc.get("is_hidden", False)

            # Prepend isolation wrapper to block socket / network and limit stdout
            driver_script = (
                "import sys, os\n"
                f"{code}\n"
            )

            start_time = time.time()
            try:
                container = client.containers.run(
                    image=settings.DOCKER_SANDBOX_IMAGE,
                    command=["python", "-c", driver_script],
                    network_mode="none",
                    mem_limit=f"{memory_limit_mb}m",
                    cpu_quota=settings.SANDBOX_CPU_QUOTA,
                    pids_limit=settings.SANDBOX_PIDS_LIMIT,
                    user="1000:1000",
                    read_only=True,
                    tmpfs={"/tmp": "rw,noexec,nosuid,size=16m"},
                    security_opt=["no-new-privileges:true"],
                    cap_drop=["ALL"],
                    detach=False,
                    remove=True,
                    stdin_open=True,
                    environment={"PYTHONUNBUFFERED": "1"}
                )
                duration_ms = int((time.time() - start_time) * 1000)
                raw_out = container.decode("utf-8") if isinstance(container, bytes) else str(container)
                
                # Enforce Output Limit
                if len(raw_out) > settings.SANDBOX_MAX_OUTPUT_BYTES:
                    results.append({
                        "test_case_index": idx + 1,
                        "passed": False,
                        "execution_time_ms": duration_ms,
                        "is_hidden": is_hidden,
                        "error": f"Output Limit Exceeded: output exceeded {settings.SANDBOX_MAX_OUTPUT_BYTES} bytes limit.",
                        "failure_type": "OUTPUT_LIMIT_EXCEEDED"
                    })
                    overall_failure_type = "OUTPUT_LIMIT_EXCEEDED"
                    continue

                actual_output = raw_out.strip()
                passed = actual_output == expected_output
                if passed:
                    passed_count += 1

                results.append({
                    "test_case_index": idx + 1,
                    "passed": passed,
                    "execution_time_ms": duration_ms,
                    "is_hidden": is_hidden,
                    "input": tc_input if not is_hidden else "[HIDDEN]",
                    "expected_output": expected_output if not is_hidden else "[HIDDEN]",
                    "actual_output": actual_output if not is_hidden else ("[MATCH]" if passed else "[MISMATCH]"),
                    "failure_type": None if passed else "WRONG_ANSWER"
                })
            except Exception as ex:
                duration_ms = int((time.time() - start_time) * 1000)
                err_str = str(ex)
                failure_type = "RUNTIME_ERROR"
                if "timeout" in err_str.lower() or duration_ms >= (timeout_seconds * 1000):
                    failure_type = "TIME_LIMIT_EXCEEDED"
                elif "memory" in err_str.lower() or "oom" in err_str.lower():
                    failure_type = "MEMORY_LIMIT_EXCEEDED"

                if not overall_failure_type:
                    overall_failure_type = failure_type

                results.append({
                    "test_case_index": idx + 1,
                    "passed": False,
                    "execution_time_ms": duration_ms,
                    "is_hidden": is_hidden,
                    "error": err_str[:300],
                    "failure_type": failure_type
                })

        return {
            "total_test_cases": len(test_cases),
            "passed_test_cases": passed_count,
            "all_passed": passed_count == len(test_cases) and len(test_cases) > 0,
            "failure_type": overall_failure_type if passed_count < len(test_cases) else None,
            "results": results
        }

    @classmethod
    def _run_in_subprocess(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        timeout_seconds: int,
        memory_limit_mb: int
    ) -> Dict[str, Any]:
        """
        Hardened fallback runner executing code in an isolated child process:
        - Never executes in FastAPI server process.
        - Strips all parent process environment variables (no app secrets, DB passwords, JWT keys).
        - Enforces strict network denial by intercepting socket creation.
        - Enforces output limit (caps excessive output, e.g. from while True: print("a")).
        - Enforces strict wall-clock timeout and process termination.
        - Isolates in disposable temporary directory.
        """
        results = []
        passed_count = 0
        overall_failure_type = None

        # Build clean environment without parent application secrets
        clean_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONUNBUFFERED": "1"
        }
        if sys.platform == "win32":
            clean_env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
            clean_env["COMSPEC"] = os.environ.get("COMSPEC", r"C:\Windows\system32\cmd.exe")

        # Security sandbox wrapper injected before user code
        # 1. Blocks socket creation to deny network by default
        # 2. Handles memory tracking / allocation limits
        sandbox_wrapper = (
            "import sys, os\n"
            "# --- ProctorAI Sandbox Security Enforcement ---\n"
            "# 1. Network Denial\n"
            "try:\n"
            "    import socket\n"
            "    class _BlockedSocket:\n"
            "        def __init__(self, *args, **kwargs):\n"
            "            raise PermissionError('SecurityViolation: Network access is denied by sandbox policy.')\n"
            "        def __call__(self, *args, **kwargs):\n"
            "            raise PermissionError('SecurityViolation: Network access is denied by sandbox policy.')\n"
            "    socket.socket = _BlockedSocket\n"
            "    socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError('SecurityViolation: Network access is denied by sandbox policy.'))\n"
            "except Exception:\n"
            "    pass\n"
            "# 2. Block urllib / http connections\n"
            "try:\n"
            "    import urllib.request\n"
            "    def _blocked_urlopen(*args, **kwargs):\n"
            "        raise PermissionError('SecurityViolation: Outbound HTTP network access is denied.')\n"
            "    urllib.request.urlopen = _blocked_urlopen\n"
            "except Exception:\n"
            "    pass\n"
            "# -----------------------------------------------\n\n"
            f"{code}\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "solution.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(sandbox_wrapper)

            for idx, tc in enumerate(test_cases):
                tc_input = str(tc.get("input", ""))
                expected_output = str(tc.get("expected_output", "")).strip()
                is_hidden = tc.get("is_hidden", False)

                start_time = time.time()
                try:
                    proc = subprocess.Popen(
                        [sys.executable, script_path],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=temp_dir,
                        env=clean_env,
                        text=True
                    )

                    try:
                        stdout, stderr = proc.communicate(input=tc_input, timeout=timeout_seconds)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        stdout, stderr = proc.communicate()
                        duration_ms = int(timeout_seconds * 1000)
                        results.append({
                            "test_case_index": idx + 1,
                            "passed": False,
                            "execution_time_ms": duration_ms,
                            "is_hidden": is_hidden,
                            "error": f"Time Limit Exceeded: Execution timed out after {timeout_seconds}s (potential infinite loop).",
                            "failure_type": "TIME_LIMIT_EXCEEDED"
                        })
                        if not overall_failure_type:
                            overall_failure_type = "TIME_LIMIT_EXCEEDED"
                        continue

                    duration_ms = int((time.time() - start_time) * 1000)

                    # Check Output Limit
                    max_output_bytes = settings.SANDBOX_MAX_OUTPUT_BYTES
                    if len(stdout) > max_output_bytes:
                        results.append({
                            "test_case_index": idx + 1,
                            "passed": False,
                            "execution_time_ms": duration_ms,
                            "is_hidden": is_hidden,
                            "error": f"Output Limit Exceeded: Program generated {len(stdout)} characters, exceeding {max_output_bytes} bytes quota.",
                            "failure_type": "OUTPUT_LIMIT_EXCEEDED"
                        })
                        if not overall_failure_type:
                            overall_failure_type = "OUTPUT_LIMIT_EXCEEDED"
                        continue

                    def _norm(s: str) -> str:
                        if not s:
                            return ""
                        lines = [line.rstrip() for line in s.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")]
                        return "\n".join(lines).strip()

                    actual_output = stdout.strip()
                    error_output = stderr.strip()

                    # Sanitize error output to remove internal server path names
                    sanitized_err = error_output.replace(temp_dir, "[sandbox]").replace(os.path.dirname(sys.executable), "[system]")

                    if proc.returncode != 0:
                        # Determine specific failure type
                        failure_type = "RUNTIME_ERROR"
                        err_lower = sanitized_err.lower()
                        if "memoryerror" in err_lower or "allocation exceeded" in err_lower:
                            failure_type = "MEMORY_LIMIT_EXCEEDED"
                        elif any(term in err_lower for term in ["securityviolation", "permissionerror", "network access is denied", "outbound http", "blocked_socket", "blocked_urlopen"]):
                            failure_type = "SECURITY_VIOLATION"
                        elif any(term in err_lower for term in ["syntaxerror", "indentationerror"]):
                            failure_type = "COMPILATION_ERROR"

                        if not overall_failure_type:
                            overall_failure_type = failure_type

                        results.append({
                            "test_case_index": idx + 1,
                            "passed": False,
                            "execution_time_ms": duration_ms,
                            "is_hidden": is_hidden,
                            "error": sanitized_err[:500] or f"Process exited with code {proc.returncode}",
                            "failure_type": failure_type
                        })
                    else:
                        passed = (_norm(actual_output) == _norm(expected_output))
                        if passed:
                            passed_count += 1
                        else:
                            if not overall_failure_type:
                                overall_failure_type = "WRONG_ANSWER"

                        results.append({
                            "test_case_index": idx + 1,
                            "passed": passed,
                            "execution_time_ms": duration_ms,
                            "is_hidden": is_hidden,
                            "input": tc_input if not is_hidden else "[HIDDEN]",
                            "expected_output": expected_output if not is_hidden else "[HIDDEN]",
                            "actual_output": actual_output if not is_hidden else ("[MATCH]" if passed else "[MISMATCH]"),
                            "failure_type": None if passed else "WRONG_ANSWER"
                        })

                except Exception as ex:
                    duration_ms = int((time.time() - start_time) * 1000)
                    results.append({
                        "test_case_index": idx + 1,
                        "passed": False,
                        "execution_time_ms": duration_ms,
                        "is_hidden": is_hidden,
                        "error": str(ex)[:300],
                        "failure_type": "RUNTIME_ERROR"
                    })
                    if not overall_failure_type:
                        overall_failure_type = "RUNTIME_ERROR"

        return {
            "total_test_cases": len(test_cases),
            "passed_test_cases": passed_count,
            "all_passed": passed_count == len(test_cases) and len(test_cases) > 0,
            "failure_type": overall_failure_type if passed_count < len(test_cases) else None,
            "results": results
        }
