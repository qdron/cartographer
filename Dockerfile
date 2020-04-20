FROM python:3.8-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apk add build-base
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./bot.py" ]