from dotenv import load_dotenv
from os import environ
from psycopg2 import connect


categories = (
    'electric_bill',
    'gas_bill',
    'oil_bill',
    'mileage',
    'flights_under_4',
    'flights_over_4',
    'recycles_newspaper',
    'recycles_aluminum_tin'
)

load_dotenv(".env")

connection = connect(environ.get('DATABASE_URL'), sslmode='require')
c = connection.cursor()


def update(text):
    c.execute(text)
    connection.commit()


def query(text):
    c.execute(text)
    return c


def create_tables():
    statements = (
        """
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY UNIQUE NOT NULL,
            name VARCHAR(100) UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY UNIQUE NOT NULL,
            name VARCHAR(100)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS input_values (
            user_id INTEGER NOT NULL,
            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            category_id INTEGER NOT NULL,
            value BIGINT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS index_newest
        ON input_values (submitted_at DESC)
        """,
    )
    upsert_statements = (
        """
        INSERT INTO users (id, name)
        VALUES (1, 'Test User')
        ON CONFLICT (id) DO NOTHING
        """,
        """
        INSERT INTO categories (name)
        VALUES
            ('electric_bill'),
            ('gas_bill'),
            ('oil_bill'),
            ('mileage'),
            ('flights_under_4'),
            ('flights_over_4'),
            ('recycles_newspaper'),
            ('recycles_aluminum_tin')
        ON CONFLICT (name) DO NOTHING
        """,
    )
    for statement in statements:
        update(statement)
    for statement in upsert_statements:
        update(statement)


weights = {
    "electric_bill": 105,
    "gas_bill": 105,
    "oil_bill": 113,
    "mileage": .79,
    "flights_under_4": 1100,
    "flights_over_4": 4400,
    "recycles_newspaper": 184,
    "recycles_aluminum_tin": 166
}


def calculate_footprint(electric_bill=0, gas_bill=0, oil_bill=0, mileage=0, flights_under_4=0, flights_over_4=0, recycles_newspaper=True, recycles_aluminum_tin=True):
    footprint = 0
    for value in categories[:-2]:
        footprint += eval(value) * weights[value]
    if not recycles_newspaper:
        footprint += weights["recycles_newspaper"]
    if not recycles_aluminum_tin:
        footprint += weights["recycles_aluminum_tin"]
    return footprint
