#! /bin/bash
# usage backup_influxdb.sh
echo 'Starting InfluxDB Backup'
docker compose exec -T backup-manager backup_influxdb.sh