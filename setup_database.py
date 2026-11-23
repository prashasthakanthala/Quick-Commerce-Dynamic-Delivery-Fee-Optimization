import pandas as pd
import sqlite3
import io

print("Step 1: Loading 50,000 random prior orders...")
orders = pd.read_csv("orders.csv")
orders = orders[orders["eval_set"] == "prior"]
sample_ids = set(orders.sample(50000, random_state=42)["order_id"])
orders = orders[orders["order_id"].isin(sample_ids)]

print("Step 2: Filtering order line items in chunks...")
chunks = pd.read_csv("order_products__prior.csv", chunksize=1_000_000)
items = pd.concat(c[c["order_id"].isin(sample_ids)] for c in chunks)

print("Step 3: Saving Instacart tables to SQLite...")
con = sqlite3.connect("blinkit_project.db")
orders.to_sql("orders", con, if_exists="replace", index=False)
items.to_sql("order_items", con, if_exists="replace", index=False)
pd.read_csv("products.csv").to_sql("products", con, if_exists="replace", index=False)
pd.read_csv("departments.csv").to_sql("departments", con, if_exists="replace", index=False)

print("Step 4: Creating lookup tables (Departments, Hours, Old Policy)...")
dept_csv = """department,margin_tier,unit_price_inr,gross_margin_pct,include_flag
frozen,Medium-Low,65,0.14,1
other,Medium,50,0.18,1
bakery,Low,35,0.07,1
produce,Medium-Low,40,0.14,1
alcohol,Excluded,0,0.00,0
international,High,120,0.28,1
beverages,Medium,45,0.20,1
dry goods pasta,Low,45,0.08,1
bulk,Low,60,0.07,1
personal care,High,140,0.30,1
meat seafood,Medium-Low,110,0.15,1
pantry,Low,50,0.08,1
breakfast,Medium,55,0.19,1
canned goods,Medium-Low,55,0.14,1
dairy eggs,Low,35,0.06,1
household,Medium,70,0.20,1
babies,High,150,0.28,1
snacks,Medium,40,0.22,1
deli,Medium-Low,75,0.15,1
missing,Medium,50,0.18,1
pets,High,130,0.28,1"""

hours_csv = """order_hour_of_day,daypart_type,rider_payout_inr,picking_packing_inr
0,Normal,32,8
1,Normal,32,8
2,Normal,32,8
3,Normal,32,8
4,Normal,32,8
5,Normal,32,8
6,Normal,32,8
7,Peak,45,10
8,Peak,45,10
9,Peak,45,10
10,Peak,45,10
11,Normal,32,8
12,Normal,32,8
13,Normal,32,8
14,Normal,32,8
15,Normal,32,8
16,Normal,32,8
17,Normal,32,8
18,Peak,45,10
19,Peak,45,10
20,Peak,45,10
21,Peak,45,10
22,Peak,45,10
23,Normal,32,8"""

old_policy_csv = """rule_order,segment_name,min_cart_inr,max_cart_inr,delivery_fee_inr
1,Old_Tiny_Cart,0,98.99,25
2,Old_Mid_Cart,99,198.99,15
3,Old_Free_Delivery,199,999999,0"""

pd.read_csv(io.StringIO(dept_csv)).to_sql("map_departments", con, if_exists="replace", index=False)
pd.read_csv(io.StringIO(hours_csv)).to_sql("map_hours", con, if_exists="replace", index=False)
pd.read_csv(io.StringIO(old_policy_csv)).to_sql("old_policy", con, if_exists="replace", index=False)

con.close()
print("DONE! blinkit_project.db is ready.")