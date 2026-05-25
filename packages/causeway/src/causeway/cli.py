"""Causeway CLI.

Each command is a thin shell over dyadpy plus the convention layer:

- ``causeway new <name>``        — scaffold a project from the template tree.
- ``causeway dev``               — owned uvicorn dev server + smart route hot-swap.
- ``causeway build``             — IR + generated client directory + wheel. ``--binary`` AOT-compiles via Nuitka.
- ``causeway freeze``            — emit the AOT build tree without compiling.
- ``causeway plugins``           — list registered adapters.
- ``causeway diff``              — delegate to ``dyadpy diff``.
- ``causeway deploy <target>``   — invoke the matching ``DeployTarget`` adapter.
- ``causeway plugin new <name>`` — scaffold a sibling plugin package.

Anything heavy (codegen, diff) is dyadpy's job; Causeway supplies the
project shape.
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
    name="causeway",
    help="A lean backend framework for type-safe Python APIs.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print the installed version."""
    try:
        v = metadata.version("causeway")
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
    """Scaffold a new Causeway app.

    Creates ``<name>/`` with ``pyproject.toml``, ``causeway.toml``, an ``.env``
    template, and the canonical ``src/app/`` tree: ``config.py``,
    ``plugins.py``, ``lifespan.py``, ``routes/_middleware.py``,
    ``routes/index.py``, ``tests/test_smoke.py``.
    """
    parent = target or Path.cwd()
    root = parent / name
    if root.exists():
        console.print(f"[red]error[/red]: {root} already exists")
        raise typer.Exit(code=1)

    from causeway._scaffold import scaffold

    scaffold(root, name)
    console.print(f"[green]created[/green] {root}")
    console.print("\nNext steps:")
    console.print(f"  cd {name}")
    console.print("  uv sync")
    console.print("  causeway dev")


@app.command()
def dev(
    module: Annotated[str, typer.Option(help="ASGI app module path.")] = "app:app",
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
) -> None:
    """Run the owned dev server with smart route hot swapping."""
    from causeway.dev import run_causeway_dev

    os.environ.setdefault("CAUSEWAY_ENV", "dev")
    project = Path.cwd()
    run_causeway_dev(
        module=module,
        host=host,
        port=port,
        project=project,
        routes_root=_discover_routes(project),
    )


@app.command()
def build(
    target: Annotated[
        Path,
        typer.Option("--target", "-o", help="Output directory."),
    ] = Path("dist"),
    module: Annotated[
        str,
        typer.Option(
            "--module",
            "-m",
            help="``module:attr`` of your ``dyadpy.App`` to introspect for codegen.",
        ),
    ] = "app:app",
    binary: Annotated[
        bool,
        typer.Option(
            "--binary",
            help="Build a self-contained AOT-compiled binary instead of a wheel. "
            "Requires `causeway[binary]`.",
        ),
    ] = False,
    sign: Annotated[
        bool,
        typer.Option("--sign", help="Sign the binary with cosign sign-blob (--binary only)."),
    ] = False,
    sbom: Annotated[
        bool,
        typer.Option("--sbom", help="Emit a CycloneDX SBOM via syft (--binary only)."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Run freeze + plan but skip the Nuitka build (--binary only).",
        ),
    ] = False,
) -> None:
    """Produce the deployable artifact.

    Default build emits three outputs into ``<target>/``: the IR snapshot
    (``ir.json``), the generated TypeScript client directory (``client/``), and
    a Python wheel.

    ``--binary`` switches to a self-contained, AOT-compiled binary
    (single-file, standalone). Requires ``pip install causeway[binary]``.

    Routes, plugins, and settings paths are discovered by convention
    (``app/routes``, ``app/plugins.py``, ``app/config.py:Settings``).
    """
    if binary:
        _build_binary(target=target, sign=sign, sbom=sbom, dry_run=dry_run)
        return

    target.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dyadpy.cli",
            "codegen",
            "--out",
            str(target / "client"),
            module,
        ],
        check=False,
    )
    if result.returncode != 0:
        console.print("[red]codegen failed[/red]")
        raise typer.Exit(code=result.returncode)
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(target)],
        check=False,
    )
    console.print(f"[green]built[/green] -> {target}")


def _build_binary(*, target: Path, sign: bool, sbom: bool, dry_run: bool) -> None:
    from causeway._binary import build_binary

    project = Path.cwd()
    artifact = build_binary(
        project_root=project,
        out=target,
        routes_root=_discover_routes(project),
        user_plugins_module=_discover_user_plugins(project),
        settings_target=_discover_settings(project),
        sign=sign,
        sbom=sbom,
        dry_run=dry_run,
    )
    if dry_run:
        console.print("[yellow]dry run[/yellow] — freeze complete, Nuitka skipped")
        return
    console.print(
        f"[green]built[/green] {artifact.path} ({artifact.size_mb:.1f} MB)",
    )
    if artifact.signature_path:
        console.print(f"  signature: {artifact.signature_path}")
    if artifact.sbom_path:
        console.print(f"  sbom: {artifact.sbom_path}")


def _discover_routes(project: Path) -> Path:
    """Convention: ``app/routes`` under cwd or ``src/``."""
    for candidate in (project / "app" / "routes", project / "src" / "app" / "routes"):
        if candidate.is_dir():
            return candidate
    console.print("[red]error[/red]: no routes directory found (looked for app/routes)")
    raise typer.Exit(code=1)


def _discover_user_plugins(project: Path) -> str | None:
    """Convention: ``app/plugins.py``. None for minimal apps."""
    for candidate in (project / "app" / "plugins.py", project / "src" / "app" / "plugins.py"):
        if candidate.is_file():
            return "app.plugins"
    return None


def _discover_settings(project: Path) -> str | None:
    """Convention: ``app/config.py`` exporting ``Settings``. None for minimal apps."""
    for candidate in (project / "app" / "config.py", project / "src" / "app" / "config.py"):
        if candidate.is_file():
            return "app.config:Settings"
    return None


@app.command()
def freeze(
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output directory for the frozen build tree."),
    ] = Path(".causeway/build"),
) -> None:
    """Generate the AOT-frozen build tree. Standalone of ``causeway build --binary``.

    Routes, plugins, and settings paths are discovered by convention
    (``app/routes``, ``app/plugins.py``, ``app/config.py:Settings``).
    """
    from causeway._freeze import freeze as _freeze

    project = Path.cwd()
    manifest = _freeze(
        routes_root=_discover_routes(project),
        out_dir=out,
        user_plugins_module=_discover_user_plugins(project),
        settings_target=_discover_settings(project),
    )
    console.print(
        f"[green]frozen[/green] {manifest.route_count} route(s), "
        f"{manifest.plugin_count} plugin(s) -> {out}/_causeway_build/",
    )


@app.command()
def plugins() -> None:
    """List currently-registered plugin adapters."""
    from causeway.plugins import registered

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

    Delegates to ``dyadpy diff``. Causeway's contribution is the project
    convention; the IR walk + classification is dyadpy's.
    """
    subprocess.run(
        [sys.executable, "-m", "dyadpy.cli", "diff", str(baseline), str(candidate)],
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
    from causeway.plugins import registered

    wanted = f"{target.lower()}deploy"
    adapter = next(
        (p for p in registered() if type(p).__name__.lower() == wanted),
        None,
    )
    if adapter is None:
        console.print(
            f"[red]no DeployTarget registered for {target!r}[/red]. "
            f"Install ``causeway-deploy-{target}`` and register it in ``plugins.py``.",
        )
        raise typer.Exit(code=1)

    package = getattr(adapter, "package", None)
    if callable(package):
        package(target_dir=output)
    console.print(f"[green]packaged[/green] -> {output}")


@app.command(name="plugin")
def plugin_new(
    action: Annotated[str, typer.Argument(help="Subcommand; only 'new' is supported.")],
    name: Annotated[str, typer.Argument(help="Plugin package name (e.g. causeway-storage-s3).")],
    target: Annotated[Path | None, typer.Option("--target", "-t")] = None,
) -> None:
    """Scaffold a new Causeway plugin package.

    ``causeway plugin new causeway-mailer-mailgun`` creates a sibling package with
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

    from causeway._scaffold import scaffold_plugin

    scaffold_plugin(root, name)
    console.print(f"[green]created[/green] plugin {name} at {root}")


def main() -> None:
    """Entry point for the ``causeway`` console script."""
    app()


if __name__ == "__main__":
    main()
