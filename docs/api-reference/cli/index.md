# CLI

The `causeway` command. Thin shell over the framework + `dyadpy`.

```
$ causeway --help
causeway — a lean backend framework for type-safe Python APIs.

Commands:
  new <name>                 Scaffold a new app.
  dev                        Run the dev server + smart route hot-swap.
  build                      Emit the IR, the TS client, and a wheel.
  plugins                    List registered plugin adapters.
  plugin new <name>          Scaffold a new plugin package.
  diff <a> <b>               Compare two IR snapshots.
  deploy <target>            Invoke the relevant deploy plugin.
  version                    Print the installed version.
```

## Per command

| Command                      | Page                            |
| ---------------------------- | ------------------------------- |
| `causeway new <name>`        | [`new`](./new.md)               |
| `causeway dev`               | [`dev`](./dev.md)               |
| `causeway build`             | [`build`](./build.md)           |
| `causeway plugins`           | [`plugins`](./plugins.md)       |
| `causeway plugin new <name>` | [`plugin new`](./plugin-new.md) |
| `causeway diff <a> <b>`      | [`diff`](./diff.md)             |
| `causeway deploy <target>`   | [`deploy`](./deploy.md)         |
| `causeway version`           | [`version`](./version.md)       |
