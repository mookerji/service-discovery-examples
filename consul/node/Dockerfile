FROM python:3.8-slim-buster
COPY ./requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y curl
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY . /app
