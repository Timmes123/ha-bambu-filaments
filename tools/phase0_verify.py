"""Phase 0 verification for the Bambu Filaments HA integration.

Verifies, against the user's own Bambu account, that a third-party client can:
  1. log in to the Bambu cloud (email code / 2FA aware),
  2. READ the Filament Manager spool inventory (GET /my/filament/v2),
  3. optionally WRITE (--write-test: harmlessly edit one spool's note and revert it).

Credentials are prompted interactively and never persisted; only the bearer
token is cached in tools/.bambu_token.json (gitignored) so re-runs skip login.

Usage:
    python tools/phase0_verify.py [--write-test] [--region global|china] [--spool-id ID]
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from pathlib import Path

TOKEN_CACHE = Path(__file__).parent / ".bambu_token.json"

# --- HTTP layer: prefer curl_cffi (TLS fingerprint), then cloudscraper, then requests ---
MECHANISM = None
try:
    from curl_cffi import requests as curl_requests
    MECHANISM = "curl_cffi"
except ImportError:
    pass
if MECHANISM is None:
    try:
        import cloudscraper
        MECHANISM = "cloudscraper"
    except ImportError:
        pass
if MECHANISM is None:
    import requests as plain_requests
    MECHANISM = "requests"

FULL_HEADERS = {
    "User-Agent": "bambu_network_agent/01.09.05.01",
    "X-BBL-Client-Name": "OrcaSlicer",
    "X-BBL-Client-Type": "slicer",
    "X-BBL-Client-Version": "01.09.05.51",
    "X-BBL-Language": "en-US",
    "X-BBL-OS-Type": "linux",
    "X-BBL-OS-Version": "6.2.0",
    "X-BBL-Agent-Version": "01.09.05.01",
    "X-BBL-Executable-info": "{}",
    "X-BBL-Agent-OS-Type": "linux",
    "accept": "application/json",
    "Content-Type": "application/json",
}


def api_base(region: str) -> str:
    return "https://api.bambulab.cn" if region == "china" else "https://api.bambulab.com"


def web_base(region: str) -> str:
    return "https://bambulab.cn" if region == "china" else "https://bambulab.com"


def http(method: str, url: str, token: str | None = None, body: dict | None = None):
    headers = {} if MECHANISM == "curl_cffi" else dict(FULL_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    kwargs = {"headers": headers, "timeout": 20}
    if body is not None:
        kwargs["json"] = body
    if MECHANISM == "curl_cffi":
        resp = getattr(curl_requests, method)(url, impersonate="chrome", **kwargs)
    elif MECHANISM == "cloudscraper":
        resp = getattr(cloudscraper.create_scraper(), method)(url, **kwargs)
    else:
        resp = getattr(plain_requests, method)(url, **kwargs)
    if resp.status_code in (403, 429) and "cloudflare" in resp.text.lower():
        print(f"  !! Blocked by Cloudflare (HTTP {resp.status_code}) via mechanism '{MECHANISM}'.")
        print("     Install curl_cffi for the best success rate: pip install curl_cffi")
        sys.exit(2)
    return resp


# --------------------------------------------------------------------------- auth

def login(region: str) -> str:
    email = input("Bambu account email: ").strip()
    password = getpass.getpass("Password (input hidden, not stored): ")
    base = api_base(region)

    resp = http("post", f"{base}/v1/user-service/user/login",
                body={"account": email, "password": password, "apiError": ""})
    data = resp.json() if resp.status_code == 200 else {}
    token = data.get("accessToken", "")
    if token:
        print("  Login OK (direct token).")
        return token

    login_type = data.get("loginType")
    if login_type == "verifyCode" or (resp.status_code == 200 and not token):
        key = "phone" if "@" not in email else "email"
        code_url = (f"{base}/v1/user-service/user/sendsmscode" if key == "phone"
                    else f"{base}/v1/user-service/user/sendemail/code")
        r = http("post", code_url, body={key: email, "type": "codeLogin"})
        print(f"  Verification code requested (HTTP {r.status_code}). Check your {key}.")
        while True:
            code = input("Enter verification code: ").strip()
            r = http("post", f"{base}/v1/user-service/user/login",
                     body={"account": email, "code": code})
            if r.status_code == 200 and r.json().get("accessToken"):
                print("  Login OK (verification code).")
                return r.json()["accessToken"]
            print(f"  Code rejected (HTTP {r.status_code}): {r.text[:200]} -- try again (Ctrl+C to abort).")
    elif login_type == "tfa":
        tfa_key = data.get("tfaKey")
        code = input("Enter 2FA (TOTP) code: ").strip()
        r = http("post", f"{web_base(region)}/api/sign-in/tfa",
                 body={"tfaKey": tfa_key, "tfaCode": code})
        token = r.cookies.get("token") if hasattr(r, "cookies") else None
        if token:
            print("  Login OK (2FA).")
            return token
        print(f"  2FA login failed (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(2)

    print(f"  Login failed (HTTP {resp.status_code}): {resp.text[:300]}")
    sys.exit(2)


def get_token(region: str) -> str:
    if TOKEN_CACHE.exists():
        cached = json.loads(TOKEN_CACHE.read_text())
        if cached.get("region") == region:
            print("Using cached token from tools/.bambu_token.json")
            return cached["token"]
    token = login(region)
    TOKEN_CACHE.write_text(json.dumps({"token": token, "region": region,
                                       "obtained_at": int(time.time())}))
    print("  Token cached locally (gitignored).")
    return token


# ---------------------------------------------------------------- filament reads

def fetch_spools(base: str, token: str) -> list[dict]:
    spools, offset, total = [], 0, None
    while True:
        r = http("get", f"{base}/v1/design-user-service/my/filament/v2?offset={offset}&limit=100",
                 token=token)
        if r.status_code == 401:
            print("  Token expired/invalid (HTTP 401). Delete tools/.bambu_token.json and re-run.")
            sys.exit(2)
        if r.status_code != 200:
            print(f"  READ FAILED: HTTP {r.status_code}: {r.text[:300]}")
            sys.exit(1)
        data = r.json()
        hits = data.get("hits") or []
        spools.extend(h for h in hits if isinstance(h, dict))
        total = data.get("total", len(spools))
        offset += len(hits)
        if not hits or offset >= total:
            return spools


def print_spools(spools: list[dict]) -> None:
    print(f"\n=== READ TEST: {len(spools)} spool(s) in the account filament library ===")
    fmt = "{:>9}  {:<12} {:<8} {:<22} {:<11} {:>7} {:>7} {:>5}  {}"
    print(fmt.format("id", "vendor", "type", "name", "color", "restg", "totalg", "pct", "location"))
    for s in spools:
        net, tot = s.get("netWeight") or 0, s.get("totalNetWeight") or 0
        pct = round(net / tot * 100) if tot else 0
        loc = f'{s.get("deviceName", "")} slot {s.get("slotId", "")}' if s.get("inPrinter") else "-"
        print(fmt.format(s.get("id", "?"), str(s.get("filamentVendor", ""))[:12],
                         str(s.get("filamentType", ""))[:8], str(s.get("filamentName", ""))[:22],
                         str(s.get("color", "")), net, tot, pct, loc))


# ---------------------------------------------------------------- write test

def write_test(base: str, token: str, spools: list[dict], spool_id: int | None) -> None:
    if not spools:
        print("\nWRITE TEST SKIPPED: no spools in library. Add one in Bambu Studio/Handy first.")
        return
    target = next((s for s in spools if s.get("id") == spool_id), spools[0]) if spool_id else spools[0]
    sid, original_note = target["id"], target.get("note") or ""
    marker_note = (original_note + " [ha-test]").strip()
    print(f"\n=== WRITE TEST on spool id {sid} ({target.get('filamentVendor')} "
          f"{target.get('filamentName')}): note -> '{marker_note}' and back ===")

    def put_note(note: str) -> bool:
        # Try full-object PUT first (mirrors what the official client sends),
        # fall back to a minimal body.
        for body in ({**target, "note": note},
                     {"id": sid, "filamentName": target.get("filamentName", ""), "note": note}):
            r = http("put", f"{base}/v1/design-user-service/my/filament/v2", token=token, body=body)
            print(f"  PUT ({'full' if body is not target and len(body) > 3 else 'minimal'} body) "
                  f"-> HTTP {r.status_code}: {r.text[:200]}")
            if r.status_code == 200:
                return True
        return False

    if not put_note(marker_note):
        print("  WRITE TEST FAILED: PUT rejected. Integration ships read-only (see SPEC phase 2).")
        return
    # verify round-trip
    fresh = next((s for s in fetch_spools(base, token) if s.get("id") == sid), None)
    if fresh and (fresh.get("note") or "") == marker_note:
        print("  Verified: note change visible on re-read.")
        ok = put_note(original_note)
        print("  Reverted note to original." if ok else
              f"  WARNING: could not revert note; restore manually in Studio/Handy (was: '{original_note}').")
        print("\n  WRITE TEST PASSED - third-party writes work.")
    else:
        got = None if fresh is None else fresh.get("note")
        print(f"  WRITE TEST INCONCLUSIVE: PUT returned 200 but re-read shows note={got!r}.")


# ---------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--region", choices=["global", "china"], default="global")
    ap.add_argument("--write-test", action="store_true",
                    help="also verify write access (edits + reverts one spool's note)")
    ap.add_argument("--spool-id", type=int, default=None,
                    help="spool id to use for the write test (default: first spool)")
    args = ap.parse_args()

    print(f"HTTP mechanism: {MECHANISM}"
          + ("" if MECHANISM == "curl_cffi" else "  (tip: pip install curl_cffi)"))
    base = api_base(args.region)
    token = get_token(args.region)

    spools = fetch_spools(base, token)
    print_spools(spools)

    # Note: despite a "no auth required" comment in the official client source,
    # this endpoint returns 401 without a token (verified 2026-08-27).
    r = http("get", f"{base}/v1/design-user-service/filament/config", token=token)
    n = len((r.json().get("filamentSettings") or [])) if r.status_code == 200 else None
    print(f"\nCatalog endpoint /filament/config: HTTP {r.status_code}"
          + (f", {n} canonical filaments" if n is not None else f": {r.text[:150]}"))

    print("\nREAD TEST PASSED." if spools or r is not None else "")
    if args.write_test:
        write_test(base, token, spools, args.spool_id)
    else:
        print("Run again with --write-test to verify write access (phase 0 gate for SPEC phase 2).")


if __name__ == "__main__":
    main()
