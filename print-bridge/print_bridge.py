#!/usr/bin/env python3
"""
Remote Print-Bridge: nimmt PDF per HTTPS entgegen und druckt über CUPS (lp).

Für Betrieb im Drucker-LAN (z. B. Proxmox LXC) — Erreichbarkeit von außen über Cloudflare Tunnel.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

DEFAULT_PORT = 8766
MAX_PDF_BYTES = 32 * 1024 * 1024
PRINTER_NAME_RE = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> dict:
    token = os.environ.get("PRINT_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("PRINT_API_TOKEN ist nicht gesetzt.")
    prefixes_raw = os.environ.get("PRINT_ALLOWED_PRINTER_PREFIXES", "").strip()
    prefixes = tuple(p.strip() for p in prefixes_raw.split(",") if p.strip())
    return {
        "token": token,
        "default_printer": os.environ.get("PRINT_DEFAULT_PRINTER", "").strip(),
        "port": int(os.environ.get("PRINT_BRIDGE_PORT", str(DEFAULT_PORT))),
        "cups_server": os.environ.get("CUPS_SERVER", "").strip(),
        "allowed_prefixes": prefixes,
        "job_dir": os.environ.get("PRINT_JOB_DIR", "/var/spool/print-bridge"),
    }


def cups_env(cups_server: str) -> dict:
    env = os.environ.copy()
    if cups_server:
        env["CUPS_SERVER"] = cups_server
    return env


def list_printers(cups_server: str) -> list[dict]:
    result = subprocess.run(
        ["lpstat", "-p"],
        capture_output=True,
        text=True,
        env=cups_env(cups_server),
        check=False,
    )
    printers: list[dict] = []
    for line in result.stdout.splitlines():
        # printer BueroDrucker is idle.
        match = re.match(r"^printer\s+(\S+)\s+(.+)$", line.strip())
        if match:
            printers.append({"name": match.group(1), "status": match.group(2)})
    return printers


def printer_allowed(name: str, prefixes: tuple[str, ...]) -> bool:
    if not PRINTER_NAME_RE.fullmatch(name):
        return False
    if not prefixes:
        return True
    return any(name.startswith(prefix) for prefix in prefixes)


def resolve_printer(requested: Optional[str], default_printer: str, prefixes: tuple[str, ...]) -> str:
    printer = (requested or default_printer or "").strip()
    if not printer:
        raise ValueError("Kein Drucker angegeben (Parameter printer oder PRINT_DEFAULT_PRINTER).")
    if not printer_allowed(printer, prefixes):
        raise ValueError(f"Drucker nicht erlaubt: {printer}")
    return printer


def submit_print_job(
    pdf_bytes: bytes,
    printer: str,
    title: str,
    cups_server: str,
    job_dir: str,
) -> dict:
    os.makedirs(job_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="job-", suffix=".pdf", dir=job_dir, delete=False) as tmp:
        tmp.write(pdf_bytes)
        path = tmp.name

    try:
        cmd = [
            "lp",
            "-d",
            printer,
            "-t",
            title[:200] or "Remote-Druck",
            path,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=cups_env(cups_server),
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "lp fehlgeschlagen").strip()
            raise RuntimeError(detail)
        job_id = proc.stdout.strip()
        return {"jobId": job_id, "printer": printer, "bytes": len(pdf_bytes)}
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


class PrintBridgeHandler(BaseHTTPRequestHandler):
    config: dict

    def log_message(self, fmt: str, *args) -> None:
        sys.stdout.write(
            "[%s] %s - %s\n" % (self.log_date_time_string(), self.address_string(), fmt % args)
        )

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _unauthorized(self) -> None:
        self._send_json(401, {"success": False, "message": "Unauthorized"})

    def _check_auth(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            return token == self.config["token"]
        # Optional: ?token= nur für Tests — Bearer bevorzugen
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        query_token = (qs.get("token") or [""])[0]
        return query_token == self.config["token"]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/v1/health":
            self._send_json(
                200,
                {
                    "success": True,
                    "service": "print-bridge",
                    "time": int(time.time()),
                    "defaultPrinter": self.config["default_printer"] or None,
                },
            )
            return

        if path == "/api/v1/printers":
            if not self._check_auth():
                self._unauthorized()
                return
            try:
                printers = list_printers(self.config["cups_server"])
                self._send_json(200, {"success": True, "printers": printers})
            except Exception as exc:
                self._send_json(500, {"success": False, "message": str(exc)})
            return

        self._send_json(404, {"success": False, "message": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") != "/api/v1/print":
            self._send_json(404, {"success": False, "message": "Not found"})
            return
        if not self._check_auth():
            self._unauthorized()
            return

        qs = parse_qs(parsed.query)
        requested_printer = (qs.get("printer") or [""])[0].strip() or None
        title = (qs.get("title") or ["Remote-Druck"])[0]

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            self._send_json(400, {"success": False, "message": "Leerer Body"})
            return
        if length > MAX_PDF_BYTES:
            self._send_json(413, {"success": False, "message": "PDF zu groß (max. 32 MB)"})
            return

        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
            self._send_json(415, {"success": False, "message": "Content-Type muss application/pdf sein"})
            return

        pdf_bytes = self.rfile.read(length)
        if not pdf_bytes.startswith(b"%PDF"):
            self._send_json(400, {"success": False, "message": "Kein gültiges PDF"})
            return

        try:
            printer = resolve_printer(
                requested_printer,
                self.config["default_printer"],
                self.config["allowed_prefixes"],
            )
            result = submit_print_job(
                pdf_bytes,
                printer,
                title,
                self.config["cups_server"],
                self.config["job_dir"],
            )
            self._send_json(200, {"success": True, **result})
        except ValueError as exc:
            self._send_json(400, {"success": False, "message": str(exc)})
        except Exception as exc:
            self._send_json(500, {"success": False, "message": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Feuerwehr Print-Bridge")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    port = args.port or config["port"]

    PrintBridgeHandler.config = config
    server = ThreadingHTTPServer((args.host, port), PrintBridgeHandler)
    print(
        f"[print-bridge] Hört auf {args.host}:{port} — CUPS={config['cups_server'] or 'lokal'}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[print-bridge] Beendet.", flush=True)


if __name__ == "__main__":
    main()
