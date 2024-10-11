#!/bin/ash

# Save env variables
env > /etc/environment

# Run cron deamon
crond -f