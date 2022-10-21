#! /bin/bash
backup_name="$1"
backup_destination_path=backups/influxdb
backup_source_path="$(realpath "$backup_name")"
database="iothub"

echo "Dropping database $database'..."
docker-compose exec -T influxdb sh -c 'influx -execute "drop database '$database'"'

echo "Restoring backup..."
docker-compose run -T backup-manager sh -c 'influxd  restore -host influxdb:8088 -db '$database' -portable '/backups/influxdb/$backup_name''