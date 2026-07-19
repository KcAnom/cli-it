# Security Policy

## Supported Versions

Only the latest release of `cli-it-hub` and the in-repo harnesses receive security
fixes.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately by emailing
**security@elev8tion.life**. Do not open a public issue for security reports.

Include:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept welcome)
- Affected component (`cli-it-hub`, `cli-it-plugin`, a harness, CI, hub site)

You should receive an acknowledgement within 72 hours.

## Design notes relevant to security

- **Registry-driven installs**: `cli-it install` executes install commands that
  come from the CLI-It registries, never from arbitrary user input. Shell
  execution is only used when a registry-trusted `install_cmd` contains shell
  operators; plain commands are executed without a shell.
- **No secrets in the repo**: analytics tokens are placeholders and telemetry is
  disabled with `CLI_HUB_NO_ANALYTICS=1`. CI upload secrets are optional and the
  workflows skip uploads when they are unset.
- **Path handling**: skill and preview file paths are resolved and restricted to
  known roots (`~/.cli-it-hub/`, `~/.cli-it/previews/`, project `.cli-it/`).
