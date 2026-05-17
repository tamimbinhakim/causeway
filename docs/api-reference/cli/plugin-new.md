# `causeway plugin new`

Scaffold a new Causeway plugin package.

```bash
causeway plugin new causeway-mailer-resend
```

## Synopsis

```
causeway plugin new <name> [--target <dir>]
```

## Arguments

| Argument           | Default       | Description                                                |
| ------------------ | ------------- | ---------------------------------------------------------- |
| `<name>`           | —             | Plugin package name (e.g. `causeway-mailer-resend`).       |
| `--target` / `-t`  | current dir   | Parent directory.                                          |

## What it creates

```
causeway-mailer-resend/
├── pyproject.toml             # with the entry-point wiring pre-filled
├── README.md
├── src/causeway_mailer_resend/
│   ├── __init__.py            # plugin(settings) callable
│   └── adapter.py             # stub adapter class
└── tests/
    └── test_smoke.py          # TestApp-based smoke test
```

## Naming convention

- Official plugins: `causeway-<role>-<impl>` (e.g. `causeway-mailer-resend`).
- Third-party: `causeway-contrib-<thing>` — distinguishes from official adapters.

## See also

- [Writing a plugin](../../building/plugins/authoring.md)
- [Plugins overview](../../building/plugins/index.md)
