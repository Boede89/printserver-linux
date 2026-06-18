#!/bin/sh
# Legt den Drucker direkt in printers.conf an (ohne lpadmin/Passwort).
# Wird vom cups-Container beim Start ausgeführt.
set -e

PRINTER_NAME="${CUPS_PRINTER_NAME:-Zentrale}"
PRINTER_URI="${CUPS_PRINTER_URI:-}"
CONF="/etc/cups/printers.conf"

if [ -z "$PRINTER_URI" ]; then
  echo "[cups-init] CUPS_PRINTER_URI nicht gesetzt — überspringe Drucker-Setup."
  exit 0
fi

if [ -f "$CONF" ] && grep -q "<Printer ${PRINTER_NAME}>" "$CONF" 2>/dev/null; then
  echo "[cups-init] Drucker ${PRINTER_NAME} bereits vorhanden."
  exit 0
fi

UUID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo 00000000-0000-0000-0000-000000000001)"
NOW="$(date +%s)"

mkdir -p /etc/cups
touch "$CONF"

cat >> "$CONF" << EOF

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
PrinterMakeModel Generic IPP Everywhere Printer
</Printer>
EOF

echo "[cups-init] Drucker ${PRINTER_NAME} → ${PRINTER_URI}"
# cupsd neu laden
if [ -f /var/run/cups/cups.pid ]; then
  kill -HUP "$(cat /var/run/cups/cups.pid)" 2>/dev/null || true
fi
