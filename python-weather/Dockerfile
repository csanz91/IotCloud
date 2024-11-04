FROM python:3.12

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
RUN pip3 install -r requirements.txt

# Bundle app source
COPY ./ /app

# Generate cache folder if it doesn't exist
RUN mkdir -p /app/cache
RUN mkdir -p /app/logs

WORKDIR /app/source
EXPOSE 5003
# ENTRYPOINT ["tail", "-f", "/dev/null"]

CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "--workers", "1", "--threads", "2", "-b", "0.0.0.0:5003", "api:app"]