FROM python:3.10

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./requirements.txt ./
COPY ./libs ./libs
RUN pip install -r requirements.txt

# Bundle app source
COPY ./ /app

# 119 is the group id of docker in ubuntu
RUN groupadd -g 119 docker 
RUN useradd -m workeruser
RUN usermod -aG docker workeruser
USER workeruser

WORKDIR /app/source
ENTRYPOINT [ "python", "monitoring.py" ] 
