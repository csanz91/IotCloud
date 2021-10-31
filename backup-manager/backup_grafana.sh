#!/bin/ash
echo 'Starting Grafana backup'
set -e

grafana_db_path=grafana.db
bck_dir=/backups/grafana
mkdir -p $bck_dir

min_dirs=16
#we are saving only last 14 backups (2 weeks)
if [ $(find "$bck_dir" -maxdepth 1 -type d | wc -l) -ge $min_dirs ]
  then find "$bck_dir" -maxdepth 1 | sort | head -n 2 | sort -r | head -n 1 | xargs rm -rf
fi

#all backups are in /backup folder
#every backup is in a folder with name which is date when a backup has been created
DATE=`date +%Y-%m-%d-%H-%M-%S`

echo "Creating backup of the Grafana database"
sqlite3 $grafana_db_path ".backup '$bck_dir/GRAFANA_BCK_$DATE'"
