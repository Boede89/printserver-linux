# Konica Minolta bizhub C250i

## Empfohlene CUPS-Einstellungen

Der **bizhub C250i** unterstützt **IPP Everywhere** (AirPrint). Im Heimnetz leitet er HTTP auf **HTTPS** um — deshalb **`ipps://`** verwenden, nicht `socket://9100`.

| Variable | Wert |
|----------|------|
| `CUPS_PRINTER_NAME` | `Zentrale` (oder frei wählbar) |
| `CUPS_PRINTER_URI` | `ipps://192.168.178.100/ipp/print` |
| `CUPS_PRINTER_MAKE_MODEL` | `KONICA MINOLTA bizhub C250i IPP` |
| `PRINT_DEFAULT_PRINTER` | gleicher Name wie `CUPS_PRINTER_NAME` |

In `.env`:

```env
CUPS_PRINTER_NAME=Zentrale
CUPS_PRINTER_URI=ipps://192.168.178.100/ipp/print
CUPS_PRINTER_MAKE_MODEL=KONICA MINOLTA bizhub C250i IPP
PRINT_DEFAULT_PRINTER=Zentrale
```

## Deploy (zwei Schritte)

### Schritt A — CUPS starten (ohne Auto-Drucker)

`cups-init` wurde entfernt — es hat vor CUPS in das Volume geschrieben und `cupsd.conf` überschrieben.

In `.env`:

```env
CUPS_AUTO_PRINTER=false
PRINT_BRIDGE_BIND=0.0.0.0
```

```bash
cd /opt/printserver
git pull
docker-compose down
docker volume rm printserver_cups_config printserver_cups_spool
docker-compose up -d
docker-compose ps    # cups muss „Up“ sein
```

### Schritt B — Drucker per Web-UI (empfohlen)

SSH-Tunnel vom PC:

```bash
ssh -L 8631:127.0.0.1:631 root@192.168.178.113
```

Browser: **http://localhost:8631** → `admin` / Passwort aus `CUPS_ADMIN_PASSWORD`

→ **Drucker hinzufügen** → **Internet Printing Protocol (ipp)**  
→ URL: `ipps://192.168.178.100/ipp/print`  
→ Treiber: **IPP Everywhere** / **KONICA MINOLTA**  
→ Name: `Zentrale`

Test:

```bash
docker-compose exec cups lpstat -p
docker-compose exec cups bash -c 'echo Test | lp -d Zentrale'
```

### Optional: Auto-Setup wieder aktivieren

Nur wenn Schritt A stabil war — sonst Restart-Loop:

```env
CUPS_AUTO_PRINTER=true
CUPS_PRINTER_URI=ipp://192.168.178.100/ipp/print
```

(`ipp://` statt `ipps://` oft stabiler in CUPS-Docker)

```bash
docker-compose down
docker volume rm printserver_cups_config
docker-compose up -d
```

## Deploy (ein Schritt, nur wenn Auto-Setup funktioniert)

## IPP-URL testen (vom LXC)

```bash
apt install -y ipp-tools
ipptool -t -V 2.0 ipps://192.168.178.100/ipp/print /usr/share/cups/ipptool/get-printer-attributes.test
```

Alternative Pfade, falls `/ipp/print` nicht geht:

- `ipps://192.168.178.100/ipp`
- `ipp://192.168.178.100/ipp/print` (nur wenn CUPS SSL-Upgrade schafft)

## Am Gerät prüfen

Am bizhub: **Einstellungen → Netzwerk → Druckerspezifikationen → IPP**  
Dort steht oft die exakte URL.

## Hinweis zu Farbe/PDF

IPP Everywhere wandelt PDF serverseitig — besser für Berichte als Raw-Port 9100.
