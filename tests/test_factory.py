from src.sandbox.factory import get_sandbox
from src.sandbox.local import LocalSandbox
from src.sandbox.docker_exec import DockerSandbox


def test_factory_default_local(monkeypatch):
    monkeypatch.delenv("SANDBOX_TYPE", raising=False)
    s = get_sandbox()
    assert isinstance(s, LocalSandbox)


def test_factory_docker_resolution(monkeypatch):
    # When docker is requested, factory should return DockerSandbox instance
    monkeypatch.setenv("SANDBOX_TYPE", "docker")
    s = get_sandbox()
    assert isinstance(s, DockerSandbox)
