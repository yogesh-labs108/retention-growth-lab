"""Run every analysis query in sql/ and save each result as a table and a CSV."""

import duckdb

from lab.config import DB_PATH, OUTPUTS, SQL_DIR


def run() -> dict:
    OUTPUTS.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    results = {}
    for path in sorted(SQL_DIR.glob("*.sql")):
        if path.name.startswith("00_"):
            continue
        name = path.stem.split("_", 1)[1]
        df = con.sql(path.read_text()).df()
        con.register("result_df", df)
        con.execute(f"create or replace table m_{name} as select * from result_df")
        con.unregister("result_df")
        df.to_csv(OUTPUTS / f"{name}.csv", index=False)
        results[name] = df
        print(f"{name}: {len(df)} rows")
    con.close()
    return results


if __name__ == "__main__":
    run()
