FROM alpine

### Dependencies
RUN set -ex && \
    apk update && \
    apk upgrade && \
    apk add --no-cache \
    influxdb \
    mongodb-tools && \
    rm -rf /usr/src/* && \
    rm -rf /root/.cache /tmp/* /var/cache/apk/*

ARG user=appuser
ARG group=appuser
ARG PUID=1000
ARG PGID=1000

# Backup script
COPY backup_influxdb.sh /bin/backup_influxdb.sh
RUN chmod +x /bin/backup_influxdb.sh
COPY backup_mongodb.sh /bin/backup_mongodb.sh
RUN chmod +x /bin/backup_mongodb.sh

# Create user
RUN addgroup  -g ${PGID} -S ${group} && adduser -u ${PUID} -S ${user} -G ${group} 

# Setup crontab
COPY cron.conf /var/spool/cron/crontabs/${user}

# Run Cron in foreground
CMD crond -l 0 -f