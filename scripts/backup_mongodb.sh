#! /bin/bash
# usage backup_mongodb.sh
echo 'Starting MongoDB Backup'
docker compose exec -u backupuser -T backup-manager backup_mongodb.sh