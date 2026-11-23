import sqlite3
import pandas as pd

print("1. Connecting to blinkit_project.db...")
con = sqlite3.connect("blinkit_project.db")

sql_script = """
DROP TABLE IF EXISTS order_unit_economics;

CREATE TABLE order_unit_economics AS
WITH valid_items AS (
    SELECT 
        oi.order_id,
        o.order_hour_of_day,
        d.department,
        m.margin_tier,
        m.unit_price_inr,
        m.unit_price_inr * m.gross_margin_pct AS item_gross_margin_inr
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN departments d ON p.department_id = d.department_id
    JOIN map_departments m ON d.department = m.department
    WHERE m.include_flag = 1
),
cart_summary AS (
    SELECT 
        order_id,
        order_hour_of_day,
        COUNT(*) AS item_count,
        ROUND(SUM(unit_price_inr), 2) AS cart_value_inr,
        ROUND(SUM(item_gross_margin_inr), 2) AS gross_margin_inr,
        ROUND(SUM(item_gross_margin_inr) / SUM(unit_price_inr), 4) AS cart_margin_pct
    FROM valid_items
    GROUP BY order_id, order_hour_of_day
    HAVING SUM(unit_price_inr) > 0
),
policy_applied AS (
    SELECT 
        c.*,
        h.daypart_type,
        h.rider_payout_inr,
        h.picking_packing_inr,
        ROUND(c.cart_value_inr * 0.015, 2) AS payment_gateway_inr,
        CASE WHEN h.daypart_type = 'Peak' THEN 50 ELSE 0 END AS peak_buffer_inr,
        CASE 
            WHEN c.cart_value_inr < 99 THEN 25
            WHEN c.cart_value_inr < 199 THEN 15
            ELSE 0 
        END AS old_delivery_fee_inr,
        CASE 
            WHEN c.cart_value_inr < 99 THEN '1_Tiny_Cart'
            WHEN c.cart_margin_pct >= 0.25 AND c.cart_value_inr >= (149 + CASE WHEN h.daypart_type = 'Peak' THEN 50 ELSE 0 END) THEN '2_High_Margin_Early_Free'
            WHEN c.cart_margin_pct < 0.12 AND c.cart_value_inr < (249 + CASE WHEN h.daypart_type = 'Peak' THEN 50 ELSE 0 END) THEN '3_Low_Margin_Staple'
            WHEN c.cart_value_inr < 199 THEN '4_Medium_Margin_Under_199'
            ELSE '5_Standard_Free_Delivery'
        END AS new_policy_segment,
        CASE 
            WHEN c.cart_value_inr < 99 THEN 35
            WHEN c.cart_margin_pct >= 0.25 AND c.cart_value_inr >= (149 + CASE WHEN h.daypart_type = 'Peak' THEN 50 ELSE 0 END) THEN 0
            WHEN c.cart_margin_pct < 0.12 AND c.cart_value_inr < (249 + CASE WHEN h.daypart_type = 'Peak' THEN 50 ELSE 0 END) THEN 15
            WHEN c.cart_value_inr < 199 THEN 15
            ELSE 0
        END AS new_delivery_fee_inr
    FROM cart_summary c
    JOIN map_hours h ON c.order_hour_of_day = h.order_hour_of_day
)
SELECT 
    *,
    ROUND(gross_margin_inr + old_delivery_fee_inr - rider_payout_inr - picking_packing_inr - payment_gateway_inr, 2) AS old_contribution_profit_inr,
    ROUND(gross_margin_inr + new_delivery_fee_inr - rider_payout_inr - picking_packing_inr - payment_gateway_inr, 2) AS new_contribution_profit_inr
FROM policy_applied;
"""

print("2. Creating order_unit_economics table...")
con.executescript(sql_script)

summary_query = """
SELECT 
    new_policy_segment,
    COUNT(*) AS total_orders,
    ROUND(AVG(cart_value_inr), 1) AS avg_cart_inr,
    ROUND(AVG(cart_margin_pct) * 100, 1) AS avg_margin_pct,
    SUM(CASE WHEN old_contribution_profit_inr < 0 THEN 1 ELSE 0 END) AS old_loss_orders,
    SUM(CASE WHEN new_contribution_profit_inr < 0 THEN 1 ELSE 0 END) AS new_loss_orders,
    ROUND(SUM(old_contribution_profit_inr), 0) AS total_old_profit_inr,
    ROUND(SUM(new_contribution_profit_inr), 0) AS total_new_profit_inr
FROM order_unit_economics
GROUP BY new_policy_segment
ORDER BY new_policy_segment;
"""

summary_df = pd.read_sql(summary_query, con)
print("\n--- BEFORE VS. AFTER PROFIT SUMMARY ---")
print(summary_df.to_string(index=False))

print("\n3. Exporting clean CSV files for Power BI & MySQL...")
pd.read_sql("SELECT * FROM order_unit_economics", con).to_csv("order_unit_economics.csv", index=False)
pd.read_sql("SELECT * FROM smart_addon_bundles", con).to_csv("smart_addon_bundles.csv", index=False)
summary_df.to_csv("policy_summary.csv", index=False)

con.close()
print("\nDONE! Saved order_unit_economics.csv, smart_addon_bundles.csv, and policy_summary.csv!")