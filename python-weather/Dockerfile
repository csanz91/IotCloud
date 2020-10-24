FROM python:3.8

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

# Generate logs folder if it doesn't exist
RUN mkdir -p /app/logs

# Generate cache folder if it doesn't exist
RUN mkdir -p /app/cache

WORKDIR /app/source
EXPOSE 5003
CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "--workers", "1", "--threads", "2", "-b", "0.0.0.0:5003", "api:app"]