"""Download the Instacart data (if missing) and build the DuckDB database."""

import sys
import urllib.request

import duckdb

from lab.config import DATASET_URL, DB_PATH, RAW, RAW_FILES, SQL_DIR


def download() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in RAW_FILES:
        target = RAW / name
        if target.exists() and target.stat().st_size > 0:
            continue
        print(f"downloading {name} ...", flush=True)
        urllib.request.urlretrieve(DATASET_URL.format(name=name), target)


def build() -> None:
    con = duckdb.connect(str(DB_PATH))
    raw = RAW.as_posix()
    con.execute(f"""
        create or replace table orders as
        select * replace (cast(order_hour_of_day as integer) as order_hour_of_day)
        from read_csv_auto('{raw}/orders.csv');
        create or replace table products as select * from read_csv_auto('{raw}/products.csv');
        create or replace table aisles as select * from read_csv_auto('{raw}/aisles.csv');
        create or replace table departments as select * from read_csv_auto('{raw}/departments.csv');
        create or replace table order_products as
            select * from read_csv_auto('{raw}/order_products__prior.csv')
            union all
            select * from read_csv_auto('{raw}/order_products__train.csv');
    """)
    con.execute((SQL_DIR / "00_facts.sql").read_text())
    for table in ["orders", "order_products", "order_facts", "user_facts"]:
        n = con.sql(f"select count(*) from {table}").fetchone()[0]
        print(f"{table:>15}: {n:,} rows")
    con.close()


if __name__ == "__main__":
    if "--skip-download" not in sys.argv:
        download()
    build()
