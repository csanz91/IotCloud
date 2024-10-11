#! /bin/bash
# usage backup_influxdb.sh
echo 'Starting InfluxDB Backup'
docker compose exec -u backupuser -T backup-manager backup_influxdb.sh
