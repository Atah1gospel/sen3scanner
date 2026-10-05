#!/usr/bin/env python3
"""
SentryScan - Web exposure & security posture scanner.

Performs passive/low-impact checks against a target and scores it:
- Security header presence (CSP, HSTS, X-Frame-Options, etc.)
- Cookie flag hygiene (Secure / HttpOnly / SameSite)
- TLS certificate validity & expiry
- Server banner disclosure
- Common exposed paths (robots.txt, .git, .env, admin panels) — GET only,
  no exploitation, just checking response codes.

Usage:
    python3 scanner.py https://example.com
    python3 scanner.py https://example.com --out report.html
"""

import argparse
import json
import socket
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from urllib.parse import urlparse

SECURITY_HEADERS = {
    "Strict-Transport-Security": "Forces HTTPS, prevents downgrade attacks",
    "Content-Security-Policy": "Mitigates XSS & data injection",
    "X-Frame-Options": "Prevents clickjacking via iframes",
    "X-Content-Type-Options": "Prevents MIME-sniffing attacks",
    "Referrer-Policy": "Controls referrer leakage",
    "Permissions-Policy": "Restricts browser feature access",
}

EXPOSED_PATHS = [
    "/robots.txt", "/sitemap.xml", "/.git/config", "/.env",
    "/wp-admin/", "/admin/", "/.well-known/security.txt",
    "/backup.zip", "/.DS_Store",
]

SEVERITY = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "SentryScan/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.getheaders()), resp.read(2048)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception:
        return None, {}, b""


def check_headers(headers):
    findings = []
    present = {k.lower(): v for k, v in headers.items()}
    for h, why in SECURITY_HEADERS.items():
        if h.lower() not in present:
            findings.append({
                "title": f"Missing header: {h}",
                "detail": why,
                "severity": "medium",
            })
    server = present.get("server")
    if server:
        findings.append({
            "title": "Server banner disclosed",
            "detail": f"Server header reveals: {server}",
            "severity": "low",
        })
    return findings


def check_cookies(headers):
    findings = []
    raw_cookies = []
    for k, v in headers.items():
        if k.lower() == "set-cookie":
            raw_cookies.append(v)
    for cookie in raw_cookies:
        name = cookie.split("=")[0]
        flags = cookie.lower()
        missing = []
        if "secure" not in flags:
            missing.append("Secure")
        if "httponly" not in flags:
            missing.append("HttpOnly")
        if "samesite" not in flags:
            missing.append("SameSite")
        if missing:
            findings.append({
                "title": f"Cookie '{name}' missing flags: {', '.join(missing)}",
                "detail": "Cookies without these flags are exposed to theft/CSRF/XSS abuse",
                "severity": "high" if "Secure" in missing else "medium",
            })
    return findings


def check_tls(hostname, port=443):
    findings = []
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        expiry = expiry.replace(tzinfo=timezone.utc)
        days_left = (expiry - datetime.now(timezone.utc)).days
        if days_left < 0:
            findings.append({"title": "TLS certificate EXPIRED", "detail": f"Expired {-days_left} days ago", "severity": "critical"})
        elif days_left < 14:
            findings.append({"title": "TLS certificate expiring soon", "detail": f"{days_left} days remaining", "severity": "high"})
        else:
            findings.append({"title": "TLS certificate valid", "detail": f"{days_left} days remaining", "severity": "info"})
    except Exception as e:
        findings.append({"title": "TLS check failed", "detail": str(e), "severity": "medium"})
    return findings


def check_exposed_paths(base_url):
    findings = []
    for path in EXPOSED_PATHS:
        status, _, _ = fetch(base_url.rstrip("/") + path)
        if status == 200:
            sev = "high" if path in (".env", ".git/config", "backup.zip") else "info"
            findings.append({
                "title": f"Accessible: {path}",
                "detail": f"Returned HTTP 200 — verify this should be public",
                "severity": sev,
            })
    return findings


def score(findings):
    penalty = sum(SEVERITY.get(f["severity"], 0) * 5 for f in findings)
    return max(0, 100 - penalty)


def grade(points):
    if points >= 90: return "A"
    if points >= 75: return "B"
    if points >= 60: return "C"
    if points >= 40: return "D"
    return "F"


def run_scan(target):
    parsed = urlparse(target if "://" in target else f"https://{target}")
    hostname = parsed.hostname
    status, headers, _ = fetch(target)

    all_findings = []
    all_findings += check_headers(headers)
    all_findings += check_cookies(headers)
    all_findings += check_exposed_paths(target)
    if parsed.scheme == "https":
        all_findings += check_tls(hostname)

    pts = score(all_findings)
    return {
        "target": target,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "http_status": status,
        "score": pts,
        "grade": grade(pts),
        "findings": sorted(all_findings, key=lambda f: -SEVERITY.get(f["severity"], 0)),
    }


def main():
    parser = argparse.ArgumentParser(description="SentryScan web exposure scanner")
    parser.add_argument("target", help="Target URL, e.g. https://example.com")
    parser.add_argument("--out", default="scan_result.json", help="JSON output path")
    args = parser.parse_args()

    print(f"[*] Scanning {args.target} ...")
    result = run_scan(args.target)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[+] Score: {result['score']}/100 (Grade {result['grade']})")
    print(f"[+] {len(result['findings'])} findings written to {args.out}")
    print("[*] Run report.py on this JSON to generate the dashboard.")


if __name__ == "__main__":
    main()
