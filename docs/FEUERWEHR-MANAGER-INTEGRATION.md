# Anbindung Feuerwehr-Manager

Im Manager gibt es bereits PDF-Export (Atemschutz, Berichte). Die **Druckerverwaltung** in den Einstellungen ist noch als „folgt später“ markiert — geplanter Ablauf:

## Zielablauf

```
Benutzer klickt „Drucken“
  → Manager erzeugt PDF (wie heute)
  → POST an Print-Bridge (Cloudflare-URL)
  → Drucker im anderen Netz druckt
```

## Konfiguration (geplant im Manager)

| Variable | Beispiel |
|----------|----------|
| `FEUERWEHR_PRINT_BRIDGE_URL` | `https://print.ihre-domain.de` |
| `FEUERWEHR_PRINT_API_TOKEN` | gleich wie `PRINT_API_TOKEN` auf dem Server |
| `FEUERWEHR_PRINT_DEFAULT_PRINTER` | `Feuerwehr_Buero` |
| `FEUERWEHR_CF_ACCESS_CLIENT_ID` | nur wenn Cloudflare Access aktiv |
| `FEUERWEHR_CF_ACCESS_CLIENT_SECRET` | nur wenn Cloudflare Access aktiv |

## API-Aufruf (Referenz)

```http
POST /api/v1/print?printer=Feuerwehr_Buero&title=Einsatzbericht HTTP/1.1
Host: print.ihre-domain.de
Authorization: Bearer <PRINT_API_TOKEN>
CF-Access-Client-Id: <optional>
CF-Access-Client-Secret: <optional>
Content-Type: application/pdf

<PDF bytes>
```

Antwort bei Erfolg:

```json
{"success": true, "jobId": "...", "printer": "Feuerwehr_Buero", "bytes": 12345}
```

## Manueller Test vom Manager-Server

```bash
curl -fsS -X POST \
  -H "Authorization: Bearer $FEUERWEHR_PRINT_API_TOKEN" \
  -H "CF-Access-Client-Id: $FEUERWEHR_CF_ACCESS_CLIENT_ID" \
  -H "CF-Access-Client-Secret: $FEUERWEHR_CF_ACCESS_CLIENT_SECRET" \
  -H "Content-Type: application/pdf" \
  --data-binary @test.pdf \
  "$FEUERWEHR_PRINT_BRIDGE_URL/api/v1/print?printer=Feuerwehr_Buero"
```

## Nächste Schritte im Manager-Repo

1. Unit-Einstellung: Print-Bridge-URL, Token, Standarddrucker
2. Service `RemotePrintService` (PDF-Bytes → HTTP POST)
3. UI: „Drucken“ neben „PDF herunterladen“
4. Admin → Schnittstellen → Druckerverwaltung aktivieren

Wenn Sie möchten, können wir das als nächstes im Feuerwehr-Manager umsetzen.
