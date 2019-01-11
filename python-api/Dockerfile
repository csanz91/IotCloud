FROM python:2.7

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

WORKDIR /app/source

EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "api:app", "--reload"]