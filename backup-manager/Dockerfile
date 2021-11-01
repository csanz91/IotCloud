FROM alpine

### Dependencies
RUN set -ex && \
    apk update && \
    apk upgrade && \
    apk add --no-cache \
    influxdb \
    sqlite \
    mongodb-tools && \
    rm -rf /usr/src/* && \
    rm -rf /root/.cache /tmp/* /var/cache/apk/*

ARG user=appuser
ARG group=appuser
ARG PUID=1000
ARG PGID=1000

# InfluxDB backup script
COPY backup_influxdb.sh /bin/backup_influxdb.sh
RUN chmod +x /bin/backup_influxdb.sh
# MongoDB backup script
COPY backup_mongodb.sh /bin/backup_mongodb.sh
RUN chmod +x /bin/backup_mongodb.sh
# Grafana backup script
COPY backup_grafana.sh /bin/backup_grafana.sh
RUN chmod +x /bin/backup_grafana.sh
# Upload backups to gdrive script
COPY upload_to_gdrive.sh /bin/upload_to_gdrive.sh
RUN chmod +x /bin/upload_to_gdrive.sh

# Create user
RUN addgroup  -g ${PGID} -S ${group} && adduser -u ${PUID} -S ${user} -G ${group} 

# Setup crontab
COPY cron.conf /var/spool/cron/crontabs/${user}

# Download gdrive, extract it and make it executable
ARG GDRIVE_URL='https://github.com/prasmussen/gdrive/releases/download/2.1.1/gdrive_2.1.1_linux_amd64.tar.gz'
RUN wget -qO- $GDRIVE_URL | tar -xvz -C .
RUN mv gdrive /bin/
RUN chmod +x /bin/gdrive

# Run Cron in foreground
CMD crond -l 0 -f