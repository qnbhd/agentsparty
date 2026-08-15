# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a vulnerability

Report privately. Do **not** open a public GitHub issue, discussion, or pull
request for a vulnerability.

1. [Open a private GitHub security advisory](https://github.com/qnbhd/agentsparty/security/advisories/new)
2. Or email [1qnbhd@gmail.com](mailto:1qnbhd@gmail.com) with a description,
   impact, and a minimal reproduction if you have one.

We aim to acknowledge a report within 7 days and to say whether we accept it
within 14 days. Fixes for accepted reports ship in the next patch of the
supported 0.1.x line when that is enough, or we will say why more time is
needed.

## Scope

In scope: the `agentsparty` library as published on PyPI, its optional `openai`
extra, and official examples when an unsafe default would be copied as-is.

Out of scope:

- Prompt injection that an application did not isolate from instructions
- Defects only in user-written tools, sandboxes, or host configuration
- Denial of service against a third-party model provider
- Issues that require a compromised local account or stolen API keys

## What the library does not do

`agentsparty` checks protocol shape. It does not sandbox tools, redact journals,
or set a transport timeout on an injected client. See the
[security page](https://qnbhd.github.io/agentsparty/docs/start/security/).
