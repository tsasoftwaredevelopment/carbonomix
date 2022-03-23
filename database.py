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


weights = {
    "electric_bill": 105,
    "gas_bill": 105,
    "oil_bill": 113,
    "mileage": .79,
    "flights_under_four": 1100,
    "flights_over_four": 4400,
    "recycles_newspaper": 184,
    "recycles_aluminum_tin": 166
}


def calculate_footprint(electric_bill, gas_bill, oil_bill, mileage, flights_under_four, flights_over_four, recycles_newspaper, recycles_aluminum_tin):
    footprint = 0
    for value in (electric_bill, gas_bill, oil_bill, mileage, flights_under_four, flights_over_four):
        footprint += value * weights[str(value)]
    if not recycles_newspaper:
        footprint += weights["recycles_newspaper"]
    if not recycles_aluminum_tin:
        footprint += weights["recycles_aluminum_tin"]
    return footprint
