FROM python:3.8

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

WORKDIR /app
COPY . /app