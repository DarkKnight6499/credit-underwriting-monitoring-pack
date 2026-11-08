"""Optional WRDS pull of month-end corporate bond records; needs a WRDS account (credentials come from pgpass, not this file)."""

import csv
from pathlib import Path

import psycopg2

# CONFIG: connection, month-end and filters.
HOST = "wrds-pgdata.wharton.upenn.edu"
PORT = 9737
DATABASE = "wrds"
WRDS_USER = "yazad_madan"
MONTH_END = "2025-12-31"
TRADE_FROM = "2025-12-01"
BOND_TYPES = ("CDEB", "CMTN")
OUTPUT = Path(__file__).resolve().parents[2] / "data" / "extension" / "raw_wrds" / "bondret_2025-12.csv"
QUERY = """select date, cusip, company_symbol, bond_type, security_level, coupon, maturity, t_date, t_volume,
t_dvolume, t_yld_pt, yield, t_spread, price_eom, price_ldm, duration, rating_cat, tmt
from wrdsapps_bondret.bondret
where date = %s and t_date >= %s and coupon > 0 and bond_type in %s and security_level = 'SEN'
and rating_num between 1 and 10 order by company_symbol, maturity"""


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with psycopg2.connect(host=HOST, port=PORT, dbname=DATABASE, user=WRDS_USER, sslmode="require", connect_timeout=60) as conn:
        cur = conn.cursor()
        cur.execute(QUERY, (MONTH_END, TRADE_FROM, BOND_TYPES))
        rows, columns = cur.fetchall(), [d[0] for d in cur.description]
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    print(len(rows), "rows ->", OUTPUT)


if __name__ == "__main__":
    main()
