#! /bin/bash
backup_name="$1"
backup_destination_path=backups/influxdb
backup_source_path="$(realpath "$backup_name")"
backup_unzipped_folder=${backup_name::-25}
database="iothub"

echo "Unziping '$backup_name'..."
unzip "$backup_source_path" -d "$backup_destination_path"
echo "Fixing backup '$backup_name'..."	
find "$backup_destination_path/$backup_unzipped_folder" -name '*.manifest.txt' -exec bash -c 'mv "$1" "${1%.manifest.txt}".manifest' - '{}' +

echo "Dropping database $database'..."
docker-compose exec -T influxdb sh -c 'influx -execute "drop database '$database'"'

echo "Restoring backup..."
docker-compose run -T backup-manager sh -c 'influxd  restore -host influxdb:8088 -db '$database' -portable '/backups/influxdb/$backup_unzipped_folder''