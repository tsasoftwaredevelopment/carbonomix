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


def update(*args):
    c.execute(*args)
    connection.commit()


def query(*args):
    c.execute(*args)
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
            category_id SMALLINT NOT NULL,
            value DECIMAL NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS index_newest
        ON input_values (submitted_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS footprints (
            user_id INTEGER NOT NULL,
            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            footprint DECIMAL NOT NULL,
            PRIMARY KEY (user_id, submitted_at),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS index_newest
        ON footprints (submitted_at DESC)
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


def get_footprint(index=0, user_id=1):
    # If index = 0, it returns the current footprint.
    # index = 1 is the first previous footprint, et cetera.
    return query(
        """
        SELECT footprint
        FROM footprints
        WHERE user_id = %s
        ORDER BY submitted_at DESC
        LIMIT 1 OFFSET %s
        """,
        (user_id, index)
    ).fetchone()[0]


def _calculate_footprint(electric_bill=0, gas_bill=0, oil_bill=0, mileage=0, flights_under_4=0, flights_over_4=0, recycles_newspaper=True, recycles_aluminum_tin=True):
    footprint = 0
    for value in categories[:-2]:
        footprint += eval(value) * weights[value]
    if not recycles_newspaper:
        footprint += weights["recycles_newspaper"]
    if not recycles_aluminum_tin:
        footprint += weights["recycles_aluminum_tin"]
    return footprint


def _get_new_footprint(user_id=1):
    h = query(
        """
        SELECT value
        FROM (
            SELECT value,
                ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY category_id, submitted_at DESC) AS row_number
            FROM input_values
        ) split
        WHERE row_number = 1
        """
    ).fetchall()
    return _calculate_footprint(*(float(h[i][0]) for i in range(len(h))))


def update_footprint(values, categories_list=categories, user_id=1):
    for i in range(len(categories_list)):
        assert len(categories_list) == len(values) and categories_list[i] in categories

        category_id = categories.index(categories_list[i]) + 1
        update(
            """
            INSERT INTO input_values (user_id, category_id, value)
            VALUES (%s, %s, %s)
            """,
            (user_id, category_id, values[i] if type(values[i]) is not bool else int(values[i]))
        )

    new_footprint = _get_new_footprint(user_id)
    update(
        """
        INSERT INTO footprints (user_id, footprint)
        VALUES (%s, %s)
        """,
        (user_id, new_footprint)
    )
