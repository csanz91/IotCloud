#! /bin/bash
# usage backup_mongodb.sh
echo 'Starting MongoDB Backup'
docker-compose exec -T backup-manager backup_mongodb.sh