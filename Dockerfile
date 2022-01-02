FROM python:3.9

WORKDIR /usr/src/ecommerce_store

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get -y install postgresql gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./entrypoint.sh .
RUN chmod +x /usr/src/ecommerce_store/entrypoint.sh
RUN sed -i 's/\r$//g' /usr/src/ecommerce_store/entrypoint.sh

COPY . .

ENTRYPOINT ["/usr/src/ecommerce_store/entrypoint.sh"]