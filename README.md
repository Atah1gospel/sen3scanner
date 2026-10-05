# SentryScan

A passive web exposure scanner that grades a target's external security
posture and renders the results as a self-contained dashboard — no server,
no dependencies beyond the Python standard library.

![grade](https://img.shields.io/badge/example.com-D-orange)

## What it checks
- **Security headers** — HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- **Cookie hygiene** — Secure / HttpOnly / SameSite flags
- **TLS certificate** — validity, expiry window
- **Server banner disclosure**
- **Exposed paths** — `.env`, `.git/config`, backup files, admin panels (status-code check only, no exploitation)

Each finding is weighted by severity into a 0–100 score and letter grade (A–F).

## Usage
```bash
python3 scanner.py https://example.com --out scan_result.json
python3 report.py scan_result.json --out dashboard.html
open dashboard.html
```

## Why this exists
Built as a fast triage tool for the recon phase of an engagement — run it
against a scope of targets before diving into manual testing, to quickly
see where the low-hanging fruit is.

## Roadmap
- [ ] Batch mode: scan a list of domains, output a comparison table
- [ ] Subresource / third-party script inventory
- [ ] CVE lookup against detected server/framework versions
- [ ] CI mode: fail a pipeline if grade drops below threshold

## Disclaimer
All checks are passive/GET-only. Only scan domains you own or are
authorized to test.
