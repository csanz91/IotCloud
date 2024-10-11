FROM alpine:3.20

### Dependencies
RUN set -ex && \
    apk update && \
    apk upgrade && \
    apk add --no-cache \
    sqlite \
    mongodb-tools \
    shadow \
    cronie \
    && { \
        echo "http://dl-cdn.alpinelinux.org/alpine/v3.17/main"; \
        echo "http://dl-cdn.alpinelinux.org/alpine/v3.17/community"; \
    } > /tmp/repo3.17 \
    && apk add --no-cache \
        --repositories-file "/tmp/repo3.17" \
        influxdb && \ 
    rm -rf /usr/src/* && \
    rm -rf /root/.cache /tmp/* /var/cache/apk/*

# Create a non-root user
RUN useradd -m backupuser

# InfluxDB backup script
COPY backup_influxdb.sh /bin/backup_influxdb.sh
RUN chmod +x /bin/backup_influxdb.sh

# MongoDB backup script
COPY backup_mongodb.sh /bin/backup_mongodb.sh
RUN chmod +x /bin/backup_mongodb.sh

# Grafana backup script
COPY backup_grafana.sh /bin/backup_grafana.sh
RUN chmod +x /bin/backup_grafana.sh

# run_cron script
COPY run_cron.sh /bin/run_cron.sh
RUN chmod +x /bin/run_cron.sh

# Setup crontab
COPY cron.conf /etc/crontabs/backupuser
RUN chown backupuser:backupuser /etc/crontabs/backupuser

RUN crontab -u backupuser /etc/crontabs/backupuser

# Switch to non-root user
CMD ["./bin/run_cron.sh"]