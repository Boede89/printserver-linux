#!/bin/sh
# Legt printers.conf an. Bei CUPS_AUTO_PRINTER=false: leere Datei (CUPS startet stabil).
set -e

AUTO="${CUPS_AUTO_PRINTER:-false}"
PRINTER_NAME="${CUPS_PRINTER_NAME:-Zentrale}"
PRINTER_URI="${CUPS_PRINTER_URI:-}"
CONF="/etc/cups/printers.conf"

mkdir -p /etc/cups

case "$(echo "$AUTO" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes|on) ;;
  *)
    echo "[cups-init] CUPS_AUTO_PRINTER=false — leere printers.conf (alte Config wird entfernt)."
    printf '%s\n' '# Kein Drucker — per CUPS-Web-UI anlegen (docs/DRUCKER-KONICA-MINOLTA.md)' > "$CONF"
    exit 0
    ;;
esac

if [ -z "$PRINTER_URI" ]; then
  echo "[cups-init] CUPS_PRINTER_URI fehlt — leere printers.conf."
  printf '%s\n' '# Kein Drucker-URI gesetzt' > "$CONF"
  exit 0
fi

UUID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo 00000000-0000-0000-0000-000000000001)"
NOW="$(date +%s)"
MAKE_MODEL="${CUPS_PRINTER_MAKE_MODEL:-Everywhere IPP Printer}"

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
PrinterMakeModel ${MAKE_MODEL}
</Printer>
EOF

echo "[cups-init] Drucker ${PRINTER_NAME} → ${PRINTER_URI}"
