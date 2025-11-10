#!/bin/sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
cp sistemapagos.db backups/sistemapagos_$TIMESTAMP.db
echo "Backup saved to backups/sistemapagos_$TIMESTAMP.db"
