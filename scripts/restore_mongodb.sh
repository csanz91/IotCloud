#! /bin/bash
# usage restore_mongodb.sh <backup_file>
echo 'Starting MongoDB Restore'
backup_name="$1"
backup_destination_path=backups/mongodb
backup_source_path="$(realpath "$backup_name")"
database="data"

echo "Dropping database $database'..."
docker compose exec -T mongodb sh -c 'mongosh '$database' --eval "db.dropDatabase()"'

echo "Restoring backup...'$backup_name'"
docker compose run --rm -T backup-manager sh -c 'mongorestore --archive --host mongodb' < "$backup_destination_path/$backup_name"