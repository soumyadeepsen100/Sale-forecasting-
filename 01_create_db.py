"""Step 1: build the SQLite database from the CSV (schema + load + views)."""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
DB = ROOT / "sales.db"
CSV = ROOT / "data" / "stores_sales_forecasting.csv"


def main():
    df = pd.read_csv(CSV, encoding="latin1")
    # Explicit M/D/YYYY parsing, stored as ISO dates so SQL date functions work
    for c in ["Order Date", "Ship Date"]:
        df[c] = pd.to_datetime(df[c], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")
    df["Postal Code"] = df["Postal Code"].astype(str).str.zfill(5)

    con = sqlite3.connect(DB)
    con.executescript((ROOT / "sql" / "schema.sql").read_text())

    customers = (df[["Customer ID", "Customer Name", "Segment"]]
                 .drop_duplicates("Customer ID")
                 .set_axis(["customer_id", "customer_name", "segment"], axis=1))
    locations = (df[["City", "State", "Postal Code", "Region"]]
                 .drop_duplicates(["City", "State", "Postal Code"])
                 .set_axis(["city", "state", "postal_code", "region"], axis=1))
    products = (df[["Product ID", "Product Name", "Sub-Category"]]
                .drop_duplicates("Product ID")
                .set_axis(["product_id", "product_name", "sub_category"], axis=1))

    customers.to_sql("customers", con, if_exists="append", index=False)
    locations.to_sql("locations", con, if_exists="append", index=False)
    products.to_sql("products", con, if_exists="append", index=False)

    loc_map = pd.read_sql("SELECT location_id, city, state, postal_code FROM locations", con)
    df = df.merge(loc_map, left_on=["City", "State", "Postal Code"],
                  right_on=["city", "state", "postal_code"])

    orders = (df[["Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID", "location_id"]]
              .drop_duplicates("Order ID")
              .set_axis(["order_id", "order_date", "ship_date", "ship_mode",
                         "customer_id", "location_id"], axis=1))
    items = (df[["Row ID", "Order ID", "Product ID", "Sales", "Quantity", "Discount", "Profit"]]
             .set_axis(["row_id", "order_id", "product_id", "sales", "quantity",
                        "discount", "profit"], axis=1))
    orders.to_sql("orders", con, if_exists="append", index=False)
    items.to_sql("order_items", con, if_exists="append", index=False)

    con.executescript((ROOT / "sql" / "views.sql").read_text())
    con.commit()

    for t in ["customers", "locations", "products", "orders", "order_items"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:12s} {n:5d} rows")
    con.close()
    print(f"Database created: {DB.name}")


if __name__ == "__main__":
    main()
