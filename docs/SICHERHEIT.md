# Sicherheit

## Schichten

1. **Cloudflare Tunnel** — kein eingehender Port an der Firewall
2. **Cloudflare Access** — wer die URL überhaupt erreichen darf
3. **`PRINT_API_TOKEN`** — wer drucken darf (pro Auftrag)
4. **`PRINT_ALLOWED_PRINTER_PREFIXES`** — optional nur bestimmte Druckernamen
5. **CUPS nur intern** — Port 631 nie im Tunnel

## PRINT_API_TOKEN

```bash
openssl rand -hex 32
```

In `.env` eintragen, nicht committen. Regelmäßig rotieren, wenn verdächtiger Traffic.

## Cloudflare Access

Für menschliche Tests: E-Mail-Policy (nur Ihr Account).

Für **Feuerwehr-Manager**: [Service Token](https://developers.cloudflare.com/cloudflare-one/identity/service-tokens/) mit eigener Allow-Policy.

Access allein ersetzt **nicht** den API-Token — beides zusammen.

## Drucker-Allowlist

In `.env`:

```env
PRINT_ALLOWED_PRINTER_PREFIXES=Feuerwehr_,Buero
```

Nur Drucker, deren Name mit diesen Präfixen beginnt, sind per API wählbar.

## Logging

Print-Bridge loggt Zeitstempel, Client-IP und Druckaufträge nach stdout:

```bash
docker compose logs -f print-bridge
```

Optional in Cloudflare: Access-Logs und Tunnel-Analytics prüfen.

## Rate Limiting (optional)

In Cloudflare → **Security** → **WAF** → Custom rule für `print.ihre-domain.de`:

- z. B. max. 30 Requests / Minute pro IP auf `/api/v1/print`

## Notfall: Token kompromittiert

1. `PRINT_API_TOKEN` in `.env` ändern
2. `docker compose up -d`
3. Cloudflare Service Token rotieren
4. Access-Logs prüfen
