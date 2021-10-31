#!/bin/ash
echo 'Starting MongoDB backup'
set -e

: ${MONGODB_HOST:?"MONGODB_HOST env variable is required"}

bck_dir=/backups/mongodb
mkdir -p $bck_dir

min_dirs=16
#we are saving only last 14 backups (2 weeks)
if [ $(find "$bck_dir" -maxdepth 1 -type d | wc -l) -ge $min_dirs ]
  then find "$bck_dir" -maxdepth 1 | sort | head -n 2 | sort -r | head -n 1 | xargs rm -rf
fi

#all backups are in /backup folder
#every backup is in a folder with name which is date when a backup has been created
DATE=`date +%Y-%m-%d-%H-%M-%S`

echo "Creating backup of all databases"
mongodump --archive=$bck_dir/"MONGODB_BCK_"$DATE --host ${MONGODB_HOST}
