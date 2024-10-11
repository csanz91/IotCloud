FROM python:3.12.4

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

# Generate cache folder if it doesn't exist
RUN mkdir -p /app/cache

WORKDIR /app/source

EXPOSE 5000
CMD ["gunicorn", "--workers", "2", "--threads", "3", "-b", "0.0.0.0:5000", "api:app"]