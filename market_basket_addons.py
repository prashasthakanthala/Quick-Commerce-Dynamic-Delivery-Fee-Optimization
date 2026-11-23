import sqlite3
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

print("1. Connecting to blinkit_project.db...")
con = sqlite3.connect("blinkit_project.db")

query = """
SELECT 
    oi.order_id,
    p.product_name,
    d.department,
    m.unit_price_inr,
    m.gross_margin_pct,
    ROUND(m.unit_price_inr * m.gross_margin_pct, 2) AS item_profit_inr
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN departments d ON p.department_id = d.department_id
JOIN map_departments m ON d.department = m.department
WHERE m.include_flag = 1
"""
df = pd.read_sql(query, con)

print("2. Filtering top 150 popular products for fast association mining...")
top_products = df["product_name"].value_counts().head(150).index
df_top = df[df["product_name"].isin(top_products)]

basket = (
    df_top.groupby(["order_id", "product_name"])["unit_price_inr"]
    .count()
    .unstack()
    .fillna(0)
)
basket = (basket > 0)

print("3. Running Apriori algorithm to find frequently bought together items...")
frequent_itemsets = apriori(basket, min_support=0.002, use_colnames=True)
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.3)

rules = rules[
    (rules["antecedents"].apply(len) == 1) & 
    (rules["consequents"].apply(len) == 1)
].copy()

rules["trigger_item"] = rules["antecedents"].apply(lambda x: list(x)[0])
rules["recommended_addon"] = rules["consequents"].apply(lambda x: list(x)[0])

prod_info = df[["product_name", "department", "unit_price_inr", "gross_margin_pct", "item_profit_inr"]].drop_duplicates()
rules = rules.merge(prod_info, left_on="recommended_addon", right_on="product_name")

smart_addons = rules[
    (rules["gross_margin_pct"] >= 0.18) & 
    (rules["unit_price_inr"].between(30, 80))
].sort_values(by=["lift", "item_profit_inr"], ascending=False)

final_addons = smart_addons[[
    "trigger_item", "recommended_addon", "department", 
    "unit_price_inr", "gross_margin_pct", "item_profit_inr", 
    "support", "confidence", "lift"
]].head(15)

final_addons.to_sql("smart_addon_bundles", con, if_exists="replace", index=False)
con.close()

print("\nTOP PROFIT-SMART ADD-ON RECOMMENDATIONS:")
print(final_addons.to_string(index=False))
print("\nDONE! Saved 'smart_addon_bundles' table to blinkit_project.db.")