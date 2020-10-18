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

WORKDIR /app/source
CMD [ "./start.sh" ] 
