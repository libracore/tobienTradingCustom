# CLAUDE.md

Guidance for working in `tobientrading_custom`, a custom **Frappe/ERPNext v15** app
(libracore AG, for Tobien Trading). It customizes core ERPNext rather than standing
alone: custom DocTypes, Customize-Form overlays on core DocTypes, client scripts,
doc-event hooks, class overrides, reports and print formats.

## Running & testing code

This app runs inside a **Frappe bench**, against a site. The checkout you are
editing may be a remote/SFTP mount where `bench` is **not** runnable locally — in
that case only static checks work here (`python -m py_compile <file>`), and server
code must be executed on the bench host:

```
bench --site <site> execute <module.dotted.path.to_function> --kwargs "{...}"
bench --site <site> console        # REPL
bench --site <site> migrate        # runs patches.txt + schema/customization sync
```

`bench execute` imports modules fresh, so it picks up edited `.py` files.

**Test data migrations non-destructively** before trusting them: run the real steps
inside a transaction and `frappe.db.rollback()` at the end. The established pattern
is a throwaway harness next to the patch (filename prefixed `_test_`/`_diag_`) that
imports the patch's functions, exercises them on real records, asserts invariants,
then rolls back — run via `bench execute`. **Delete these harnesses when done**
(they must not ship).

## Repository layout

```
tobientrading_custom/                 # app root
  hooks.py                            # all framework wiring (see below)
  modules.txt                         # module: "Tobientrading Custom"
  __init__.py                         # __version__
  patches.txt                         # migration registry (INI format, see below)
  patches/<name>/<name>.py            # data migrations (+ __init__.py)
  tobientrading_custom/
    custom/<doctype>.json             # Customize Form overlays on CORE doctypes
    doctype/<name>/                   # this app's own DocTypes
    doctype/.../<name>.py|.js|.json   # controller / client / schema
    report/, print_format/, workspace/
    utils.py                          # shared whitelisted helpers
  overrides/                          # python class overrides (override_doctype_class)
  public/js/<doctype>.js              # client scripts (wired via doctype_js)
  public/css/
```

## hooks.py — where customization lives

- `doctype_js` / `doctype_list_js` → client scripts in `public/js/` (e.g. `Item` →
  `public/js/item.js`).
- `doc_events` → server hooks; note most submittable docs call
  `utils.attach_pdf_hook` `on_submit`.
- `override_doctype_class` → python subclasses in `tobientrading_custom/overrides/`
  (e.g. `third_party_address.py` overrides Quotation/Sales Order/.../Purchase
  Invoice to relax upstream validation).
- `jinja.methods`, `app_include_js/css`, `fixtures` (Print Formats).

Depends on `erpnextswiss` (imported in `utils.py`) in addition to frappe/erpnext.

## Customizations vs. custom DocTypes

- Changes to **core/ERPNext** DocTypes (extra fields, property setters, form layout)
  are **Customize Form exports** in `tobientrading_custom/custom/<doctype>.json`,
  flagged `sync_on_migrate: 1`. `bench migrate` applies them via
  `sync_customizations()`. Example: `Batch.package_weight` (Float) lives in
  `custom/batch.json`. Edit these by exporting from the Customize Form UI, not by
  hand, where possible.
- This app's **own** DocTypes live under `tobientrading_custom/doctype/<name>/` and
  are synced by `sync_all()`.

## Patches & migrations — read before adding one

Layout: group a release's patches in a **version folder** that matches
`__version__` — `patches/v<major>_<minor>_<patch>/<patch_name>.py` (e.g.
`patches/v0_4_0/eliminate_item_variants.py`) with an empty `__init__.py` in the
folder. Bump `__version__` in `tobientrading_custom/__init__.py` to that same
version in the same change. (A few older patches live in per-patch subfolders such
as `patches/migrate_crm_notes_to_comments/...`; that style is legacy — use version
folders for new patches.) Register every patch in `patches.txt`. House style: raw
`frappe.db.sql`, `print()` progress, copyright header
`# Copyright (c) <year>, libracore AG and contributors`.

### `patches.txt` is parsed as an INI file (configparser)

- Use `[pre_model_sync]` / `[post_model_sync]` section headers. **Every** patch line
  must sit under a header — a bare line before any header raises
  `MissingSectionHeaderError`, the parser silently falls back to "old format", and a
  header like `[post_model_sync]` then gets treated as a patch name →
  `AppNotInstalledError: App [post_model_sync] is not installed`.
- `#` comment lines are allowed under a section.

### Migrate phase order (`frappe/migrate.py`)

```
[pre_model_sync] patches  →  sync_all() (DocType schemas)  →  [post_model_sync] patches
                                                            →  sync_fixtures() / sync_customizations() / after_migrate
```

Consequences:
- Put data migrations that touch this app's own DocTypes (or read up-to-date schema)
  in **`[post_model_sync]`**, so `sync_all()` has created/updated their tables first.
- **Custom Fields (`custom/*.json`) are synced AFTER all patches** (in
  `sync_customizations()`), so a patch CANNOT assume a brand-new custom field exists
  yet. If a patch must write to one introduced in the same release, guard with
  `frappe.db.has_column(...)` and create the single field on demand via
  `create_custom_fields({...})` (depends only on the core DocType — do **not**
  call whole-app `sync_customizations()` from a patch; it pulls in unrelated files
  that may reference app DocTypes not yet present, e.g. `Allowed Pallet Type` in
  `sales_order.json`).
- App DocTypes referenced by customizations only exist after `sync_all()`.

### Other patch gotchas

- Patches run with **per-record commits** where written that way — an aborted run
  leaves committed partial work. For a destructive migration, restore the DB before
  re-running rather than relying on a partial re-run.
- Decisions evaluated against **live data at migrate time** (e.g. "is this in
  stock?") may differ from a previous run if the data changed.

## Stock / inventory domain notes (ERPNext v15 specifics here)

- Default valuation method is **FIFO** (Stock Settings).
- Batches are tracked **two ways at once**: directly via `Stock Ledger Entry.batch_no`,
  and via **Serial and Batch Bundle** (`SLE.serial_and_batch_bundle` → child
  `Serial and Batch Entry` rows, whose `qty` is **signed** like the SLE). Any
  batch-balance computation must combine both sources.
- `tabBatch.batch_qty` is a maintained, reliable stored field for current batch
  stock (sums to `Bin.actual_qty` per item).
- `Bin` has a unique index `unique_item_warehouse` on `(item_code, warehouse)` — you
  cannot relabel several items' bins onto one without merging/deleting first.
- **Period closing blocks stock-valuation reposts** (e.g. "Due to period closing, you
  cannot repost item valuation before <date>"). This makes
  `frappe.rename_doc("Item", ..., merge=True)` fail, because it triggers a repost.
  To merge/relabel items without a repost: move every `Link`-to-Item reference with
  raw SQL (discover them from `tabDocField`/`tabCustom Field` where
  `fieldtype='Link' AND options='Item'`), recompute only the warehouse-level running
  balance where needed, rebuild `Bin`s, and delete the source item with
  `frappe.delete_doc` (keeps Frappe's link-integrity check). Relabeling rows does not
  change quantities, so no repost is required.

## Conventions

- Commit messages: prefix with the issue number — `#<n> - <description>`
  (e.g. `#49 - ...`). Branches are named like `49-gebinde`.
- Python files carry the libracore copyright header.
- Bump `__version__` in `tobientrading_custom/__init__.py` for releases, and put that
  release's patches under the matching `patches/v<x>_<y>_<z>/` folder.
