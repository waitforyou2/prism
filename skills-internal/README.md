# Prism Internal

This directory contains an internal-network-oriented copy of the Prism skills.

Behavior differences from the main `skills/` tree:

- `skills-internal/harvest` disables SSL certificate verification for bundled Python and Node fetch scripts.
- `skills-internal/harvest` now uses a two-step fetch flow: Python downloads HTML locally, then Node + Defuddle parse local HTML.
- `skills-internal/prism` and `skills-internal/router` are copied as-is to keep behavior aligned with the main version.

The main `skills/` directory remains unchanged.
