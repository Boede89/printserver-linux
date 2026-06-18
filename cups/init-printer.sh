#!/bin/sh
# Legt den Drucker in printers.conf an (ohne lpadmin/Passwort).
set -e

PRINTER_NAME="${CUPS_PRINTER_NAME:-Zentrale}"
PRINTER_URI="${CUPS_PRINTER_URI:-}"
CONF="/etc/cups/printers.conf"

if [ -z "$PRINTER_URI" ]; then
  echo "[cups-init] CUPS_PRINTER_URI nicht gesetzt — überspringe Drucker-Setup."
  exit 0
fi

UUID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo 00000000-0000-0000-0000-000000000001)"
NOW="$(date +%s)"

# Konica Minolta bizhub: IPPS mit selbstsigniertem Zertifikat
SSL_OPTS="${CUPS_SSL_OPTIONS:-AllowAnyRoot,AllowExpired,AllowSelfSigned}"

mkdir -p /etc/cups

cat > "$CONF" << EOF
# Automatisch erzeugt von cups-init
<Printer ${PRINTER_NAME}>
PrinterId 1
UUID ${UUID}
AuthInfoRequired none
State Idle
StateTime ${NOW}
ConfigTime ${NOW}
Reason none
Accepting Yes
Shared No
JobSheets none none
QuotaPeriod 0
PageLimit 0
KLimit 0
OpPolicy default
device-uri ${PRINTER_URI}
PrinterInfo ${PRINTER_NAME}
PrinterMakeModel ${CUPS_PRINTER_MAKE_MODEL:-KONICA MINOLTA bizhub C250i IPP}
Option cupsSSLOptions ${SSL_OPTS}
</Printer>
EOF

echo "[cups-init] Drucker ${PRINTER_NAME} → ${PRINTER_URI}"
