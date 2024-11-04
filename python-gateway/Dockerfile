FROM python:3.13

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

WORKDIR /app/source

ENTRYPOINT [ "python", "gateway.py" ] 