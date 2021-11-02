#!/bin/ash
echo 'Starting backups upload'

backup_folder=`cat /run/secrets/gdrive_backup_folder`
gdrive -c / --service-account /run/secrets/gdrive_config sync upload --delete-extraneous /backups/ $backup_folder