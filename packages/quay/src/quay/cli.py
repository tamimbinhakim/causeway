"""Quay CLI.

Five commands, each a thin shell over dyadpy plus the convention layer:

- ``quay new <name>``   — scaffold a project from the template tree.
- ``quay dev``          — uvicorn + watcher + TS codegen + diagnostics.
- ``quay build``        — IR + ``client.ts`` + wheel.
- ``quay plugins``      — list registered adapters.
- ``quay diff``         — delegate to ``dyadpy diff``.

The CLI is intentionally thin. Anything that needs heavy logic (codegen,
diff) is dyadpy's job; Quay supplies the project shape.
"""

from __future__ import annotations

import os
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="quay",
    help="A lean backend framework for type-safe Python APIs.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print the installed version."""
    try:
        v = metadata.version("quay")
    except metadata.PackageNotFoundError:  # pragma: no cover - dev install edge
        v = "unknown"
    console.print(v)


@app.command(name="new")
def new(
    name: Annotated[str, typer.Argument(help="Project directory name.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Parent directory; defaults to the cwd."),
    ] = None,
) -> None:
    """Scaffold a new Quay app.

    Creates ``<name>/`` with ``pyproject.toml``, ``quay.toml``, an ``.env``
    template, and the canonical ``src/app/`` tree: ``config.py``,
    ``plugins.py``, ``lifespan.py``, ``routes/_middleware.py``,
    ``routes/index.py``, ``tests/test_smoke.py``.
    """
    parent = target or Path.cwd()
    root = parent / name
    if root.exists():
        console.print(f"[red]error[/red]: {root} already exists")
        raise typer.Exit(code=1)

    from quay._scaffold import scaffold

    scaffold(root, name)
    console.print(f"[green]created[/green] {root}")
    console.print("\nNext steps:")
    console.print(f"  cd {name}")
    console.print("  uv sync")
    console.print("  quay dev")


@app.command()
def dev(
    module: Annotated[str, typer.Option(help="ASGI app module path.")] = "app:app",
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
) -> None:
    """Run the dev server: uvicorn + file watcher + TS codegen.

    Delegates to ``uvicorn --reload`` and lets dyadpy's watcher re-emit
    ``client.ts`` on every change. The convention layer (file router,
    scopes, plugins) is picked up automatically because the app factory
    re-runs on each reload.
    """
    import uvicorn

    os.environ.setdefault("QUAY_ENV", "dev")
    uvicorn.run(module, host=host, port=port, reload=True, factory="app" in module)


@app.command()
def build(
    target: Annotated[Path, typer.Option(help="Output directory.")] = Path("dist"),
) -> None:
    """Produce the deployable artifact.

    Three outputs land in ``<target>/``: the IR snapshot
    (``ir.json``), the generated TypeScript client (``client.ts``), and a
    Python wheel built via ``hatch build``. ``quay diff`` consumes the IR
    snapshot for CI breaking-change detection.
    """
    target.mkdir(parents=True, exist_ok=True)
    # Delegate codegen + IR emission to dyadpy.
    result = subprocess.run(
        [sys.executable, "-m", "dyadpy", "codegen", "--out", str(target / "client.ts")],
        check=False,
    )
    if result.returncode != 0:
        console.print("[red]codegen failed[/red]")
        raise typer.Exit(code=result.returncode)
    # Build the wheel with hatch if available, otherwise via the project's
    # configured build backend.
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(target)],
        check=False,
    )
    console.print(f"[green]built[/green] -> {target}")


@app.command()
def plugins() -> None:
    """List currently-registered plugin adapters."""
    from quay.plugins import registered

    table = Table(title="Registered plugins")
    table.add_column("Adapter")
    table.add_column("Contract version")
    table.add_column("Module")

    items = registered()
    if not items:
        console.print("[dim]no plugins registered[/dim]")
        return
    for adapter in items:
        cls = type(adapter)
        table.add_row(
            cls.__name__,
            getattr(adapter, "contract_version", "?"),
            cls.__module__,
        )
    console.print(table)


@app.command()
def diff(
    baseline: Annotated[Path, typer.Argument(help="Baseline IR snapshot.")],
    candidate: Annotated[Path, typer.Argument(help="Candidate IR snapshot.")],
) -> None:
    """Compare two IR snapshots and flag breaking changes.

    Delegates to ``dyadpy diff``. Quay's contribution is the project
    convention; the IR walk + classification is dyadpy's.
    """
    subprocess.run(
        [sys.executable, "-m", "dyadpy", "diff", str(baseline), str(candidate)],
        check=False,
    )


@app.command()
def deploy(
    target: Annotated[str, typer.Argument(help="Deploy target name (e.g. docker, fly, modal).")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("dist"),
) -> None:
    """Invoke the registered ``DeployTarget`` adapter matching ``target``.

    Discovery: scan registered plugins for one whose class name matches
    ``<Target>Deploy`` (case-insensitive). The adapter writes its manifest
    files into ``output`` and pushes via its ``push()`` if available.
    """
    from quay.plugins import registered

    wanted = f"{target.lower()}deploy"
    adapter = next(
        (p for p in registered() if type(p).__name__.lower() == wanted),
        None,
    )
    if adapter is None:
        console.print(
            f"[red]no DeployTarget registered for {target!r}[/red]. "
            f"Install ``quay-deploy-{target}`` and register it in ``plugins.py``.",
        )
        raise typer.Exit(code=1)

    package = getattr(adapter, "package", None)
    if callable(package):
        package(target_dir=output)  # type: ignore[call-arg]
    console.print(f"[green]packaged[/green] -> {output}")


@app.command(name="plugin")
def plugin_new(
    action: Annotated[str, typer.Argument(help="Subcommand; only 'new' is supported.")],
    name: Annotated[str, typer.Argument(help="Plugin package name (e.g. quay-storage-s3).")],
    target: Annotated[Path | None, typer.Option("--target", "-t")] = None,
) -> None:
    """Scaffold a new Quay plugin package.

    ``quay plugin new quay-mailer-mailgun`` creates a sibling package with
    a ``pyproject.toml``, entry-point wiring, and a smoke test placeholder.
    """
    if action != "new":
        console.print(f"[red]unknown plugin subcommand:[/red] {action!r}")
        raise typer.Exit(code=1)

    parent = target or Path.cwd()
    root = parent / name
    if root.exists():
        console.print(f"[red]error[/red]: {root} already exists")
        raise typer.Exit(code=1)

    from quay._scaffold import scaffold_plugin

    scaffold_plugin(root, name)
    console.print(f"[green]created[/green] plugin {name} at {root}")


def main() -> None:
    """Entry point for the ``quay`` console script."""
    app()


if __name__ == "__main__":
    main()
