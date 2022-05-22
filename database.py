from dotenv import load_dotenv
from os import environ, getcwd, path
import sys

from psycopg2 import connect
from datetime import datetime


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

category_names = (
    'Monthly Electric Bill',
    'Monthly Gas Bill',
    'Monthly Oil Bill',
    'Yearly Mileage',
    'Yearly Flights Under 4 Hours',
    'Yearly Flights Over 4 Hours',
    'Recycles Newspaper',
    'Recycles Aluminum and Tin'
)

category_value_formats = (
    "${:,.2f}",
    "${:,.2f}",
    "${:,.2f}",
    "{:,.2f} mpg",
    "{:,.0f}",
    "{:,.0f}",
    "{:s}",
    "{:s}"
)

extend_data_directory = getcwd()

if getattr(sys, 'frozen', False):
    extend_data_directory = sys._MEIPASS

load_dotenv(dotenv_path=path.join(extend_data_directory, '.env'))
connection = connect(environ.get('DATABASE_URL'), sslmode='require')
c = connection.cursor()


def close():
    c.close()
    connection.close()


def update(*args):
    c.execute(*args)
    connection.commit()
    return c


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
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(60) NOT NULL
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
    upsert_statements = (  # TODO: Re-hash password.
        """
        INSERT INTO users (username, password)
        VALUES ('test', 'kljsdfjkldsf')
        ON CONFLICT (username) DO NOTHING
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
    values = query(
        """
        SELECT footprint
        FROM footprints
        WHERE user_id = %s
        ORDER BY submitted_at DESC
        LIMIT 1 OFFSET %s
        """,
        (user_id, index)
    ).fetchone()
    return values[0] if values else None


def _calculate_footprint(electric_bill=0, gas_bill=0, oil_bill=0, mileage=0, flights_under_4=0, flights_over_4=0, recycles_newspaper=True, recycles_aluminum_tin=True):
    footprint = 0
    for value in categories[:-2]:
        footprint += eval(value) * weights[value]
    if not recycles_newspaper:
        footprint += weights["recycles_newspaper"]
    if not recycles_aluminum_tin:
        footprint += weights["recycles_aluminum_tin"]
    return footprint


def get_current_values(date=None, user_id=1):
    h = query(
        f"""
        SELECT value
        FROM (
            SELECT value,
                ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY category_id, submitted_at DESC) AS row_number
            FROM input_values
            WHERE user_id = %s{" AND submitted_at <= %s" if date else ""}
        ) split
        WHERE row_number = 1
        """,
        (user_id,) + ((date,) if date else ())
    ).fetchall()
    return tuple(float(h[i][0]) for i in range(len(h)))


def _get_new_footprint(date=None, user_id=1):
    return _calculate_footprint(*get_current_values(date, user_id))


def update_footprint(values, categories_list=categories, date=None, user_id=1):
    if date is None:
        tz = query(
            """
            SELECT submitted_at
            FROM footprints
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()[0].tzinfo
        date = datetime.now(tz)

    insert_values = f"""
        INSERT INTO input_values (user_id, category_id, value{", submitted_at" if date else ""})
        VALUES """

    for i in range(len(categories_list)):
        assert len(categories_list) == len(values) and categories_list[i] in categories

        category_id = categories.index(categories_list[i]) + 1
        quote = "'"
        insert_values += f"({user_id}, {category_id}, {values[i] if type(values[i]) is not bool else int(values[i])}{', ' + quote + str(date) + quote if date else ''}), "

    if not insert_values.endswith("VALUES "):
        update(insert_values[:-2])
    new_footprint = _get_new_footprint(date, user_id)
    old_footprint = query(
        """
        SELECT footprint
        FROM footprints
        WHERE user_id = %s
        ORDER BY submitted_at DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    if old_footprint and new_footprint == float(old_footprint[0]):
        return

    update(
        f"""
        INSERT INTO footprints (user_id, footprint{", submitted_at" if date else ""})
        VALUES (%(user_id)s, %(new_footprint)s{", %(date)s" if date else ""})
        ON CONFLICT ON CONSTRAINT footprints_pkey
        DO UPDATE SET footprint = %(new_footprint)s
        """,
        {'user_id': user_id, 'new_footprint': new_footprint, 'date': date}
    )


def _recalculate_footprints(user_id=1):
    update(
        """
        DELETE FROM footprints
        """
    )
    dates = query(
        """
        SELECT submitted_at
        FROM input_values
        WHERE user_id = %s
        ORDER BY submitted_at DESC
        """,
        (user_id,)
    ).fetchall()
    for i in range(len(dates)):
        print(i)
        if dates[i][0] == dates[i-1][0]:
            continue

        update_footprint(tuple(), tuple(), dates[i][0], user_id)

    print("Complete.")


def _generate_data(user_id=1):
    from random import uniform, randint
    from datetime import datetime, timedelta

    """ranges = [
        ((80, 90), (40, 50)),  # electric_bill
        ((20, 40), (50, 70)),  # gas_bill
        (250, 450),  # oil_bill
        (20000, 26000),  # mileage
        (1, 4),  # flights_under_4
        (0, 1),  # flights_over_4
        (0, 1),  # recycles_newspaper
        (0, 1),  # recycles_aluminum_tin
    ]"""

    """ranges = [
        ((35, 60), (20, 40)),  # electric_bill
        ((20, 35), (30, 50)),  # gas_bill
        (200, 350),  # oil_bill
        (18000, 23000),  # mileage
        (1, 4),  # flights_under_4
        (0, 2),  # flights_over_4
        (0, 1),  # recycles_newspaper
        (0, 1),  # recycles_aluminum_tin
    ]"""

    ranges = [
        ((95, 105), (55, 65)),  # electric_bill
        ((30, 50), (60, 80)),  # gas_bill
        (290, 490),  # oil_bill
        (24000, 30000),  # mileage
        (1, 4),  # flights_under_4
        (0, 1),  # flights_over_4
        (0, 1),  # recycles_newspaper
        (0, 1),  # recycles_aluminum_tin
    ]

    update("""DELETE FROM input_values""")
    update("""DELETE FROM footprints""")

    years = 20

    date = datetime.now() - timedelta(days=365.25 * years)

    for year in range(years):
        yearly_category_indices = (3, 4, 5)
        new_yearly_values = []
        for category in yearly_category_indices:
            new_yearly_values.append(uniform(*ranges[category]) if category == 3 else randint(*ranges[category]))

        update_footprint(
            new_yearly_values,
            tuple(categories[i] for i in yearly_category_indices),
            date,
            user_id
        )

        for month in range(12 + (year == years - 1)):
            print(date)
            monthly_category_indices = (0, 1, 2, -1, -2)
            new_monthly_values = []
            for category in monthly_category_indices:
                new_monthly_values.append(uniform(*ranges[category] if category not in (0, 1) else ranges[category][int(date.month in (12, 1, 2))]) if category >= 0 else randint(*ranges[category]))

            update_footprint(
                new_monthly_values,
                tuple(categories[i] for i in monthly_category_indices),
                date,
                user_id
            )
            date += timedelta(days=(datetime(date.year, (date.month % 12) + 1, 1) - timedelta(days=1)).day)
            r = (1/1.0009, 1/1.0017)
            for i in range(2):
                ranges[i] = ((ranges[i][0][0] * uniform(*r), ranges[i][0][1] * uniform(*r)), (ranges[i][1][0] * uniform(*r), ranges[i][1][1] * uniform(*r)))
            for i in range(2, 3):
                ranges[i] = (ranges[i][0] * uniform(*r), ranges[i][1] * uniform(*r))

    print(ranges)
    print(date)
    print("Complete.")


# _generate_data()
