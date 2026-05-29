# `causeway freeze`

Emit the AOT build tree without compiling the final binary.

```bash
causeway freeze --out .causeway/build
```

## Synopsis

```
causeway freeze [--out <dir>]
```

## Options

| Option         | Default           | Description                                 |
| -------------- | ----------------- | ------------------------------------------- |
| `--out` / `-o` | `.causeway/build` | Output directory for the frozen build tree. |

## What It Captures

`freeze` discovers the app by convention:

- `app/routes` or `src/app/routes`
- `app/plugins.py` or `src/app/plugins.py`
- `app/config.py:Settings` or `src/app/config.py:Settings`

It writes a self-contained build tree with frozen route metadata, plugin metadata, settings metadata, and the generated startup path used by `causeway build --binary`.

Use this command to inspect or debug the binary build plan without paying the compile cost.

## See Also

- [`build`](./build.md)
- [Binary export](../../deploy/binary.md)
