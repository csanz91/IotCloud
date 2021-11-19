#!/bin/ash
echo 'Starting Grafana backup'
set -e

grafana_db_path=/grafana.db
bck_dir=/backups/grafana
mkdir -p $bck_dir

# Save last weeks backup and the first backup of each month
find "$bck_dir" -maxdepth 1 ! -name '*[0-9][0-9][0-9][0-9]-[0-9][0-9]-01-*' -mtime +7 -exec rm -r {} \;

#all backups are in /backup folder
#every backup is in a folder with name which is date when a backup has been created
DATE=`date +%Y-%m-%d-%H-%M-%S`

echo "Creating backup of the Grafana database"
sqlite3 $grafana_db_path ".backup '$bck_dir/GRAFANA_BCK_$DATE'"
