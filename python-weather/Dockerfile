FROM python:3.8

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

WORKDIR /app/source
EXPOSE 5003
CMD ["gunicorn", "--workers", "2", "--threads", "2", "-b", "0.0.0.0:5003", "api:app", "--reload"]