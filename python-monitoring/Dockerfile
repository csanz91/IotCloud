FROM python:3.12.4

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

WORKDIR /app/source
ENTRYPOINT [ "python", "monitoring.py" ] 
