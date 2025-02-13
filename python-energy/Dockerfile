FROM python:3.13

# Accept USER_ID and GROUP_ID arguments
ARG USER_ID=1000
ARG GROUP_ID=1000

# Install cron
RUN apt-get update && apt-get install -y cron

# Create app directory
WORKDIR /app

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && \
    touch /app/logs/cron.log && \
    chown -R ${USER_ID}:${GROUP_ID} /app/logs /app/logs/cron.log

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

# Set up cron job with environment
COPY crontab /etc/cron.d/energy-cron
RUN chmod 0644 /etc/cron.d/energy-cron

# Create script to update cron environment and start cron
RUN echo '#!/bin/bash\n\
env | grep -E "INFLUXDB_|DOCKER_" >> /etc/cron.d/energy-cron\n\
crontab /etc/cron.d/energy-cron\n\
cron -f' > /entrypoint.sh && \
chmod +x /entrypoint.sh

# Use the new entrypoint script
CMD ["/entrypoint.sh"]
