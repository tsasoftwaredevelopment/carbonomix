from dotenv import load_dotenv
from os import environ
from psycopg2 import connect

load_dotenv(".env")

connection = connect(environ.get('DATABASE_URL'))
c = connection.cursor()


def update(text):
    c.execute(text)
    connection.commit()


def query(text):
    c.execute(text)
    return c
