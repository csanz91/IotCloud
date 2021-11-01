#!/bin/ash
echo 'Starting backups upload'

cp /run/secrets/gdrive_config /gdrive/config/
backup_folder=`cat /run/secrets/gdrive_backup_folder`
gdrive -c /gdrive/config/ --service-account gdrive_config sync upload --delete-extraneous /backups/ $backup_folder