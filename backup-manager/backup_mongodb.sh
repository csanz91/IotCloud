#!/bin/ash
echo 'Starting MongoDB backup'
set -e

: ${MONGODB_HOST:?"MONGODB_HOST env variable is required"}

bck_dir=/backups/mongodb
mkdir -p $bck_dir

# Save last weeks backup and the first backup of each month
find "$bck_dir" -maxdepth 1 ! -name '*[0-9][0-9][0-9][0-9]-[0-9][0-9]-01-*' -mtime +7 -exec rm -r {} \;

#all backups are in /backup folder
#every backup is in a folder with name which is date when a backup has been created
DATE=`date +%Y-%m-%d-%H-%M-%S`

echo "Creating backup of all databases"
mongodump --archive=$bck_dir/"MONGODB_BCK_"$DATE --host ${MONGODB_HOST}
