FROM alpine:3.18

# Install dig to retrieve public IP address
RUN apk add bind-tools curl tzdata bash

WORKDIR /dynhost

COPY crontab        /var/spool/cron/crontabs/root
COPY update-record  update-record
COPY entrypoint     entrypoint

ENTRYPOINT [ "/dynhost/entrypoint" ]
