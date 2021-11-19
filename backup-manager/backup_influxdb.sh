#!/bin/ash
echo 'Starting InfluxDB backup'
set -e

: ${INFLUXDB_HOST:?"INFLUXDB_HOST env variable is required"}

bck_dir=/backups/influxdb
mkdir -p $bck_dir

# Save last weeks backup and the first backup of each month
find "$bck_dir" -maxdepth 1 ! -name '*[0-9][0-9][0-9][0-9]-[0-9][0-9]-01-*' -mtime +7 -exec rm -r {} \;

#all backups are in /backup folder
#every backup is in a folder with name which is date when a backup has been created
DATE=`date +%Y-%m-%d-%H-%M-%S`

echo "Creating backup of all databases"
influxd backup -portable -host $INFLUXDB_HOST:8088 $bck_dir/"INFLUXDB_BCK_"$DATE
