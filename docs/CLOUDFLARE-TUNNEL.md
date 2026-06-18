# Cloudflare Tunnel für den Printserver

Sie haben `cloudflared` bereits auf dem Proxmox-Server — damit reicht es, den **Print-Bridge** lokal zu starten und eine **Ingress-Regel** hinzuzufügen.

## Prinzip

- Print-Bridge lauscht nur auf **`127.0.0.1:8766`** (Standard in `docker-compose.yml`).
- `cloudflared` auf demselben Host leitet `https://print.ihre-domain.de` → `http://127.0.0.1:8766`.
- Am Router muss **kein** Port geöffnet werden.
- CUPS (`631`) bleibt **nur intern**.

## Schritt 1: Print-Bridge starten

```bash
cd /opt/printserver
cp .env.example .env
nano .env   # PRINT_API_TOKEN setzen
docker compose up -d --build

curl -fsS http://127.0.0.1:8766/api/v1/health
```

## Schritt 2: Ingress in cloudflared

### Variante A — bestehende Config-Datei erweitern

Typischer Pfad: `/etc/cloudflared/config.yml`

```yaml
tunnel: <Ihre-Tunnel-UUID>
credentials-file: /etc/cloudflared/<Ihre-Tunnel-UUID>.json

ingress:
  # … Ihre bestehenden Hostnamen …

  - hostname: print.ihre-domain.de
    service: http://127.0.0.1:8766

  # Catch-all immer zuletzt
  - service: http_status:404
```

Dann:

```bash
sudo cloudflared tunnel route dns <tunnel-name> print.ihre-domain.de
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

### Variante B — Beispiel aus diesem Repo

```bash
sudo cp /opt/printserver/cloudflared/config.example.yml /etc/cloudflared/config.yml
# UUID und Pfade anpassen
sudo systemctl restart cloudflared
```

Beispiel liegt unter [`cloudflared/config.example.yml`](../cloudflared/config.example.yml).

## Schritt 3: Cloudflare Access (stark empfohlen)

Ohne Access ist die URL zwar durch den API-Token geschützt, aber weltweit scannbar. Besser:

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → **Access** → **Applications**
2. **Add application** → Self-hosted
3. Domain: `print.ihre-domain.de`
4. Policy: z. B. nur Ihre E-Mail (`Allow` → Emails ending in `@…`)

### Feuerwehr-Manager (Server-zu-Server)

Für automatischen Druck vom Manager-Server ohne Browser-Login:

1. Access → **Service Auth** → **Service Tokens** → Token anlegen
2. Policy: `Service Auth` → dieses Token erlauben
3. Im Manager (später) zusätzliche Header mitsenden:

```
CF-Access-Client-Id: <client-id>
CF-Access-Client-Secret: <client-secret>
Authorization: Bearer <PRINT_API_TOKEN>
```

Details: [FEUERWEHR-MANAGER-INTEGRATION.md](FEUERWEHR-MANAGER-INTEGRATION.md)

## Schritt 4: Test von außen

Vom Handy (ohne WLAN zum Drucker-Netz) oder vom Manager-Server:

```bash
export URL=https://print.ihre-domain.de
export TOKEN=<PRINT_API_TOKEN>

# Health (öffentlich — nur Status)
curl -fsS "$URL/api/v1/health"

# Mit Access + Token (Service Token Header ggf. ergänzen)
curl -fsS -H "Authorization: Bearer $TOKEN" "$URL/api/v1/printers"

curl -fsS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/pdf" \
  --data-binary @test.pdf \
  "$URL/api/v1/print?printer=BueroDrucker&title=Test"
```

## cloudflared auf demselben Host vs. LXC

| Setup | Ingress-Ziel |
|-------|----------------|
| Docker auf **Proxmox-Host**, cloudflared auf Host | `http://127.0.0.1:8766` |
| Docker im **LXC**, cloudflared auf Host | `http://<LXC-IP>:8766` und in Compose `PRINT_BRIDGE_BIND=0.0.0.0` **nur** im LXC-Firewall absichern |
| cloudflared im **gleichen LXC** wie Print-Bridge | `http://127.0.0.1:8766` (bevorzugt) |

Empfehlung: Print-Bridge + cloudflared auf **demselben** System, Bridge nur localhost.

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| 502 Bad Gateway | `docker compose ps`, Bridge auf 8766? `curl localhost:8766/api/v1/health` |
| 404 von Cloudflare | DNS `print.` auf Tunnel? `cloudflared tunnel route dns` |
| 401 Unauthorized | `PRINT_API_TOKEN` / Bearer-Header prüfen |
| Access-Login statt API | Service Token für Server, oder Policy anpassen |
| Druck kommt nicht an | `docker compose logs print-bridge`, CUPS-Druckername `lpstat -p` |

## Was Sie nicht tun sollten

- Drucker-IPP (`ipp://…`) als Cloudflare-Ingress eintragen
- CUPS-Port `631` im Tunnel veröffentlichen
- `PRINT_API_TOKEN` in URLs (`?token=`) in Produktion nutzen
