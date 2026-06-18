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

## Deploy

```bash
cd /opt/printserver
git pull
docker-compose down
docker volume rm printserver_cups_config   # einmalig, alte kaputte Config löschen
docker-compose up -d
docker-compose exec cups lpstat -p
docker-compose exec cups bash -c 'echo Test | lp -d Zentrale'
```

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
