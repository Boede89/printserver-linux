# Proxmox: Printserver-LXC von null einrichten

Diese Anleitung geht davon aus:

- **Proxmox-Host** mit `cloudflared` (Cloudflare Tunnel) — z. B. wie beim Feuerwehr-Manager
- **Drucker** in einem anderen VLAN/Netz, vom Proxmox-Host oder LXC erreichbar
- **GitHub-Repo:** [github.com/Boede89/printserver-linux](https://github.com/Boede89/printserver-linux)

## Übersicht

| Schritt | Was |
|--------|-----|
| 1 | LXC-Container anlegen |
| 2 | Docker + Projekt installieren |
| 3 | Drucker in CUPS einrichten |
| 4 | Cloudflare Tunnel (Ingress-Zeile) |
| 5 | Test von außen |

---

## Schritt 1: LXC in Proxmox anlegen

### Variante A — Proxmox Web-UI (empfohlen)

1. Proxmox → **Create CT**
2. **General**
   - CT ID: z. B. `120` (frei wählen)
   - Hostname: `printserver`
   - Password: sicheres Root-Passwort
3. **Template:** `debian-12-standard` (oder aktuelles Debian-12-Template)
4. **Disks:** 8 GB (reicht)
5. **CPU:** 1 Core
6. **Memory:** 1024 MB
7. **Network** — **wichtig:**
   - Bridge: dieselbe wie das **Drucker-Netzwerk** (z. B. `vmbr1` / VLAN des Drucker-Standorts)
   - IPv4: DHCP oder statisch (z. B. `192.168.20.10/24`)
   - Wenn der Drucker nur in diesem VLAN erreichbar ist, muss der LXC hier hängen
8. **DNS:** Gateway des VLANs, DNS wie im Netz üblich
9. **Options:**
   - **Unprivileged container:** an (Standard)
   - **Nesting:** **aktivieren** (für Docker nötig)  
     → nach Erstellung: CT → Options → Features → `nesting=1`, `keyctl=1`

10. Container **starten**

### Variante B — Proxmox-Host führt cloudflared, LXC nur Drucken

Wenn `cloudflared` auf dem **Proxmox-Host** (nicht im LXC) läuft:

- LXC bekommt eine IP im Drucker-Netz (z. B. `192.168.20.10`)
- In `.env` später: `PRINT_BRIDGE_BIND=0.0.0.0`
- Ingress in cloudflared: `http://192.168.20.10:8766`
- Proxmox-Firewall: Port 8766 nur vom Host (`192.168.x.1`) zum LXC erlauben

**Einfacher:** `cloudflared` und Printserver im **gleichen** LXC — dann Ingress `http://127.0.0.1:8766`.

### Erste Anmeldung im LXC

```bash
# Vom Proxmox-Host
pct enter 120

# Oder per SSH (wenn Sie SSH im LXC aktivieren)
apt update && apt upgrade -y
apt install -y curl git ca-certificates
```

---

## Schritt 2: Docker im LXC

```bash
apt install -y docker.io docker-compose-plugin
systemctl enable --now docker
docker --version
```

Falls Docker startet mit Fehler „permission denied“ / cgroup: Features `nesting` und `keyctl` prüfen (siehe oben).

---

## Schritt 3: Projekt von GitHub

```bash
mkdir -p /opt/printserver
cd /opt/printserver
git clone https://github.com/Boede89/printserver-linux.git .
cp .env.example .env
nano .env
```

In `.env` mindestens setzen:

```env
PRINT_API_TOKEN=<openssl rand -hex 32>
PRINT_DEFAULT_PRINTER=Feuerwehr_Buero
PRINT_BRIDGE_BIND=127.0.0.1
CUPS_ADMIN_PASSWORD=<starkes Passwort>
```

Starten:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8766/api/v1/health
```

Erwartung: `{"success": true, "service": "print-bridge", ...}`

---

## Schritt 4: Drucker in CUPS

### CUPS-Web (nur vom LXC aus)

SSH-Tunnel vom PC:

```bash
ssh -L 8631:127.0.0.1:631 root@<LXC-IP>
```

Browser: `http://localhost:8631` — Login `admin` / Passwort aus `CUPS_ADMIN_PASSWORD`

Drucker hinzufügen → **Internet Printing Protocol (IPP)** → URL z. B.:

```
ipp://192.168.20.50/ipp/print
```

(Name je nach Hersteller — bei Brother/Kyocera/Epson in der Drucker-Doku nach „IPP-URL“ suchen.)

### Oder per Kommandozeile

```bash
docker compose exec cups lpadmin -p Feuerwehr_Buero -E \
  -v ipp://192.168.20.50/ipp/print -m everywhere
docker compose exec cups lpoptions -d Feuerwehr_Buero
docker compose exec cups lpstat -p
```

Testdruck:

```bash
docker compose exec cups bash -c 'echo Test | lp -d Feuerwehr_Buero'
```

API-Test (im LXC):

```bash
TOKEN=<Ihr PRINT_API_TOKEN>
curl -fsS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8766/api/v1/printers
# PDF-Test wenn Sie eine test.pdf haben:
curl -fsS -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/pdf" \
  --data-binary @test.pdf \
  "http://127.0.0.1:8766/api/v1/print?printer=Feuerwehr_Buero&title=Test"
```

---

## Schritt 5: Cloudflare Tunnel

Ausführlich: [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md)

### cloudflared auf demselben LXC (empfohlen)

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | gpg --dearmor -o /usr/share/keyrings/cloudflare-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-archive-keyring.gpg] https://pkg.cloudflare.com/cloudflared jammy main" > /etc/apt/sources.list.d/cloudflared.list
apt update && apt install -y cloudflared
```

Tunnel einrichten (falls noch keiner für diesen Host):

```bash
cloudflared tunnel login
cloudflared tunnel create printserver
cloudflared tunnel route dns printserver print.ihre-domain.de
```

`/etc/cloudflared/config.yml`:

```yaml
tunnel: <UUID aus cloudflared tunnel list>
credentials-file: /etc/cloudflared/<UUID>.json

ingress:
  - hostname: print.ihre-domain.de
    service: http://127.0.0.1:8766
  - service: http_status:404
```

```bash
systemctl enable --now cloudflared
systemctl status cloudflared
```

### cloudflared läuft schon auf dem Proxmox-Host

Nur eine Zeile in der **bestehenden** Host-`config.yml`:

```yaml
  - hostname: print.ihre-domain.de
    service: http://<LXC-IP>:8766
```

Im LXC `.env`: `PRINT_BRIDGE_BIND=0.0.0.0` und Firewall beachten.

---

## Schritt 6: Cloudflare Access (empfohlen)

Zero Trust → Access → Application für `print.ihre-domain.de`  
Policy: nur Ihre E-Mail oder **Service Token** für den Feuerwehr-Manager.

Siehe [SICHERHEIT.md](SICHERHEIT.md).

---

## Schritt 7: Test von außen

Vom Handy (Mobiles Netz) oder Laptop:

```bash
curl -fsS https://print.ihre-domain.de/api/v1/health
```

Mit Token (und ggf. Access Service-Token-Headern):

```bash
curl -fsS -H "Authorization: Bearer $TOKEN" \
  https://print.ihre-domain.de/api/v1/printers
```

---

## Checkliste

- [ ] LXC im **Drucker-VLAN**, nesting aktiv
- [ ] `docker compose ps` — beide Container `running`
- [ ] `lpstat -p` zeigt Drucker
- [ ] `curl localhost:8766/api/v1/health` OK
- [ ] Cloudflare Ingress + DNS
- [ ] `PRINT_API_TOKEN` gesetzt, nicht in Git
- [ ] CUPS Port 631 **nicht** öffentlich
- [ ] Proxmox-Snapshot nach erfolgreichem Test

---

## Typische Fehler

| Symptom | Lösung |
|---------|--------|
| Docker startet nicht im LXC | `nesting=1`, `keyctl=1` |
| Drucker nicht erreichbar | Ping vom LXC zur Drucker-IP; falsches VLAN |
| 502 über Cloudflare | Bridge läuft? `curl 127.0.0.1:8766/api/v1/health` |
| 401 bei Druck | `Authorization: Bearer` + Token prüfen |
| Leere Warteschlange, kein Papier | CUPS-Logs: `docker compose logs cups` |

---

## Wartung

```bash
cd /opt/printserver
git pull
docker compose up -d --build
```

Backup: Proxmox-Snapshot des LXC; CUPS-Konfiguration liegt im Docker-Volume `cups_config`.
