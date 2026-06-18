# Printserver (Feuerwehr / Remote-Druck)

Kleiner **Print-Bridge** für einen Drucker in einem anderen Netzwerk. PDFs kommen per HTTPS an; der Rechner im Drucker-LAN druckt lokal über CUPS.

**Erreichbarkeit von außen:** über **Cloudflare Tunnel** (`cloudflared`) — kein VPN, kein Port-Forwarding an der Fritzbox.

## Architektur

```
[ Feuerwehr-Manager / Handy / unterwegs ]
              │
              │  HTTPS  print.ihre-domain.de
              ▼
[ Cloudflare Edge ]  ← TLS, DDoS-Schutz, optional Access
              │
              │  cloudflared-Tunnel (bereits auf Proxmox)
              ▼
[ Proxmox / LXC im Drucker-Netz ]
   └── Print-Bridge  :8766  (nur localhost)
   └── CUPS          :631   (nur intern, nie öffentlich)
              │
              ▼
        Netzwerkdrucker
```

## Schnellstart

```bash
git clone https://github.com/Boede89/printserver-linux.git /opt/printserver
cd /opt/printserver
cp .env.example .env
# PRINT_API_TOKEN: openssl rand -hex 32
docker compose up -d --build
```

**Cloudflare Tunnel** um eine Zeile ergänzen (Details: [docs/CLOUDFLARE-TUNNEL.md](docs/CLOUDFLARE-TUNNEL.md)):

```yaml
ingress:
  - hostname: print.ihre-domain.de
    service: http://127.0.0.1:8766
  - service: http_status:404
```

Drucker in CUPS einrichten → Test von außen:

```bash
curl -fsS https://print.ihre-domain.de/api/v1/health
curl -fsS -H "Authorization: Bearer IHR_TOKEN" \
  https://print.ihre-domain.de/api/v1/printers
```

## Sicherheit (kurz)

| Schicht | Zweck |
|---------|--------|
| Cloudflare Tunnel | Kein offener Port am Router |
| Cloudflare Access (empfohlen) | Nur Sie / der Manager-Server dürfen die URL aufrufen |
| `PRINT_API_TOKEN` | Zusätzlich bei jedem Druckauftrag (Bearer) |

**Niemals** CUPS (Port 631) oder den Drucker selbst ins Internet legen.

## Dokumentation

- **[Proxmox LXC von null](docs/PROXMOX-SETUP.md)** — Container anlegen, Docker, Drucker, Tunnel
- [Cloudflare Tunnel](docs/CLOUDFLARE-TUNNEL.md)
- [Sicherheit](docs/SICHERHEIT.md)
- [Feuerwehr-Manager-Anbindung](docs/FEUERWEHR-MANAGER-INTEGRATION.md)

Repository: [github.com/Boede89/printserver-linux](https://github.com/Boede89/printserver-linux)

## API (Kurz)

| Methode | Pfad | Auth |
|---------|------|------|
| GET | `/api/v1/health` | nein |
| GET | `/api/v1/printers` | Bearer |
| POST | `/api/v1/print?printer=Name&title=...` | Bearer, Body: PDF |

Header: `Authorization: Bearer <PRINT_API_TOKEN>`
