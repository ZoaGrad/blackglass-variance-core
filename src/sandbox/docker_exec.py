import os
import tempfile
import time
from typing import Optional

from .base import CodeSandbox, ExecutionResult


class DockerSandbox(CodeSandbox):
    """Docker-based sandbox (opt-in).

    This implementation performs lazy imports and graceful error handling so that
    environments without Docker SDK or daemon do not crash the application. It
    returns a structured error via ExecutionResult when unavailable.
    """

    def _docker_available(self) -> tuple[bool, Optional[str]]:
        try:
            import docker  # type: ignore

            try:
                client = docker.from_env()
                # ping the daemon to verify connectivity
                client.ping()
                return True, None
            except Exception as exc:  # daemon not reachable
                return False, f"Docker daemon not available: {exc}"
        except Exception as exc:  # SDK not installed
            return False, f"Docker SDK not installed: {exc}"

    def execute(self, code: str, language: str = "python", timeout: int = 30) -> ExecutionResult:
        ok, reason = self._docker_available()
        start = time.time()
        if not ok:
            return ExecutionResult(
                stdout="",
                stderr=reason or "Docker not available",
                exit_code=1,
                duration=time.time() - start,
                meta={
                    "runtime": "docker",
                    "timed_out": False,
                    "truncated": False,
                },
            )

        if language.lower() != "python":
            return ExecutionResult(
                stdout="",
                stderr=f"Unsupported language: {language}",
                exit_code=1,
                duration=time.time() - start,
                meta={"runtime": "docker", "timed_out": False, "truncated": False},
            )

        # Lazy imports only after availability confirmed
        import docker  # type: ignore

        image = os.getenv("DOCKER_IMAGE", "python:3.11-slim")
        network_enabled = os.getenv("DOCKER_NETWORK_ENABLED", "false").lower() == "true"
        cpu_limit = os.getenv("DOCKER_CPU_LIMIT", "0.5")
        mem_limit = os.getenv("DOCKER_MEMORY_LIMIT", "256m")

        client = docker.from_env()

        # Prepare a temp script file, then mount/run inside container
        with tempfile.TemporaryDirectory(prefix="ag_sbx_dk_") as tmpdir:
            script_path = os.path.join(tmpdir, "main.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            mounts = {tmpdir: {"bind": "/work", "mode": "ro"}}

            command = ["python", "/work/main.py"]

            try:
                container = client.containers.run(
                    image=image,
                    command=command,
                    volumes=mounts,
                    network_disabled=(not network_enabled),
                    mem_limit=mem_limit,
                    nano_cpus=int(float(cpu_limit) * 1e9),  # approximate CPU limit
                    detach=True,
                    stdout=True,
                    stderr=True,
                    working_dir="/work",
                    remove=True,
                )

                try:
                    exit_code = container.wait(timeout=timeout)["StatusCode"]
                except Exception:
                    # timeout enforcement: kill the container
                    try:
                        container.kill()
                    except Exception:
                        # Best-effort cleanup: ignore errors if the container is already
                        # stopped, missing, or cannot be killed. The timeout result below
                        # is returned to the caller regardless of kill() success.
                        pass
                    return ExecutionResult(
                        stdout="",
                        stderr=f"Execution timed out after {timeout}s",
                        exit_code=-1,
                        duration=time.time() - start,
                        meta={
                            "runtime": "docker",
                            "timed_out": True,
                            "truncated": False,
                        },
                    )

                logs = container.logs(stdout=True, stderr=True)
                out = logs.decode("utf-8", errors="ignore")
                # Split rough stdout/stderr is non-trivial; return all in stdout for now
                return ExecutionResult(
                    stdout=out,
                    stderr="",
                    exit_code=int(exit_code),
                    duration=time.time() - start,
                    meta={
                        "runtime": "docker",
                        "timed_out": False,
                        "truncated": False,
                    },
                )
            except Exception as exc:
                return ExecutionResult(
                    stdout="",
                    stderr=f"Docker execution error: {exc}",
                    exit_code=1,
                    duration=time.time() - start,
                    meta={"runtime": "docker", "timed_out": False, "truncated": False},
                )
