import importlib


def test_module_imports_and_has_version() -> None:
    mod = importlib.import_module("quay")
    version = getattr(mod, "__version__", None)
    assert isinstance(version, str)
    assert version
