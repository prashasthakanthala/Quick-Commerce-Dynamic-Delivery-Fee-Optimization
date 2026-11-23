import matplotlib
matplotlib.use("Agg")  # Ensures clean PNG export on Windows
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

print("1. Loading exported CSV results...")
orders_df = pd.read_csv("order_unit_economics.csv")
summary_df = pd.read_csv("policy_summary.csv")
addons_df = pd.read_csv("smart_addon_bundles.csv")

avg_order_profit = orders_df["old_contribution_profit_inr"].mean()
penalized_df = orders_df[orders_df["new_policy_segment"].isin(["1_Tiny_Cart", "3_Low_Margin_Staple"])]
n_penalized = len(penalized_df)
base_policy_gain = (orders_df["new_contribution_profit_inr"] - orders_df["old_contribution_profit_inr"]).sum()

scenarios = [
    {"name": "Conservative\n(Worst Case)", "cancel": 0.20, "churn": 0.08, "attach": 0.10, "hm_lift": 0.00},
    {"name": "Moderate\n(Base Case)",     "cancel": 0.10, "churn": 0.04, "attach": 0.25, "hm_lift": 0.02},
    {"name": "Aggressive\n(Best Case)",   "cancel": 0.05, "churn": 0.01, "attach": 0.35, "hm_lift": 0.05},
]

avg_penalized_new_profit = penalized_df["new_contribution_profit_inr"].mean()
hm_orders = len(orders_df[orders_df["new_policy_segment"] == "2_High_Margin_Early_Free"])
hm_avg_profit = orders_df[orders_df["new_policy_segment"] == "2_High_Margin_Early_Free"]["new_contribution_profit_inr"].mean()

scen_results = []
for s in scenarios:
    cancel_impact = -(n_penalized * s["cancel"] * avg_penalized_new_profit)
    ltv_loss = -(n_penalized * s["churn"] * avg_order_profit)
    staple_count = len(orders_df[orders_df["new_policy_segment"] == "3_Low_Margin_Staple"])
    attach_gain = staple_count * s["attach"] * (12.50 - 15.00)
    lift_gain = hm_orders * s["hm_lift"] * hm_avg_profit
    
    net_uplift = base_policy_gain + cancel_impact + ltv_loss + attach_gain + lift_gain
    scen_results.append({
        "Scenario": s["name"],
        "Net_Profit_Uplift_INR": round(net_uplift, 0),
        "LTV_Churn_Cost_INR": round(ltv_loss, 0)
    })

scen_df = pd.DataFrame(scen_results)
scen_df.to_csv("sensitivity_scenarios.csv", index=False)

print("2. Drawing Executive Dashboard...")
fig = plt.figure(figsize=(16, 10), facecolor="#F8F9FA")
fig.suptitle("Quick-Commerce Dynamic Delivery Fee & Cart Profitability Optimization\n(50,000-Order Sample | Assumption-Driven Unit Economics & Market Basket Engine)", 
             fontsize=15, fontweight="bold", y=0.97, color="#1A1A1A")

old_loss_pct = (orders_df["old_contribution_profit_inr"] < 0).mean() * 100
new_loss_pct = (orders_df["new_contribution_profit_inr"] < 0).mean() * 100
mod_uplift = scen_df.loc[1, "Net_Profit_Uplift_INR"]

kpis = [
    ("Orders Analyzed", f"{len(orders_df):,}", "#2B2D42"),
    ("Loss-Making Orders (Old -> New)", f"{old_loss_pct:.1f}% -> {new_loss_pct:.1f}%", "#D90429"),
    ("Direct Policy Profit Gain", f"+Rs.{base_policy_gain:,.0f}", "#2A9D8F"),
    ("Moderate Scenario Net Uplift", f"+Rs.{mod_uplift:,.0f}", "#1D3557"),
]

for idx, (label, val, col) in enumerate(kpis):
    ax_kpi = fig.add_axes([0.05 + idx*0.235, 0.82, 0.21, 0.09])
    ax_kpi.set_facecolor("white")
    ax_kpi.set_xticks([]); ax_kpi.set_yticks([])
    for spine in ax_kpi.spines.values():
        spine.set_edgecolor(col); spine.set_linewidth(2)
    ax_kpi.text(0.5, 0.65, val, ha="center", va="center", fontsize=14, fontweight="bold", color=col)
    ax_kpi.text(0.5, 0.25, label, ha="center", va="center", fontsize=9.5, color="#555555")

# Chart 1
ax1 = fig.add_axes([0.05, 0.46, 0.42, 0.30])
ax1.grid(axis="y", linestyle="--", alpha=0.5)
segs = ["Tiny Cart\n(<Rs.99)", "High-Margin\nEarly Free", "Low-Margin\nStaples", "Med-Margin\n(<Rs.199)", "Standard\nFree"]
x = np.arange(len(segs))
w = 0.35
ax1.bar(x - w/2, summary_df["total_old_profit_inr"]/1000, w, label="Old Policy (Flat Rs.199)", color="#ADB5BD")
ax1.bar(x + w/2, summary_df["total_new_profit_inr"]/1000, w, label="New Dynamic Policy", color="#F4A261")
ax1.axhline(0, color="black", linewidth=0.8)
ax1.set_title("1. Total Contribution Profit by Segment (Rs. Thousands)", fontweight="bold", fontsize=11)
ax1.set_xticks(x); ax1.set_xticklabels(segs, fontsize=8.5)
ax1.set_ylabel("Profit / Loss (Rs. '000)")
ax1.legend(fontsize=9)

# Chart 2
ax2 = fig.add_axes([0.54, 0.46, 0.41, 0.30])
ax2.grid(True, linestyle="--", alpha=0.5)
hourly = orders_df.groupby("order_hour_of_day")[["old_contribution_profit_inr", "new_contribution_profit_inr"]].mean()
ax2.plot(hourly.index, hourly["old_contribution_profit_inr"], marker="o", label="Old Avg Profit/Order", color="#E63946", linewidth=2)
ax2.plot(hourly.index, hourly["new_contribution_profit_inr"], marker="s", label="New Avg Profit/Order", color="#2A9D8F", linewidth=2)
ax2.axvspan(7, 10, color="#FFD166", alpha=0.3, label="Modeled Peak Rush (Rs.45 Rider)")
ax2.axvspan(18, 22, color="#FFD166", alpha=0.3)
ax2.set_title("2. Hourly Avg Profit/Order (Instacart Hour Proxy + Modeled Surge)", fontweight="bold", fontsize=11)
ax2.set_xlabel("Hour of Day (0-23)"); ax2.set_ylabel("Avg Profit / Order (Rs.)")
ax2.legend(fontsize=8, loc="lower right")

# Chart 3
ax3 = fig.add_axes([0.05, 0.08, 0.38, 0.29])
ax3.grid(axis="y", linestyle="--", alpha=0.5)
colors_scen = ["#E76F51", "#2A9D8F", "#264653"]
bars = ax3.bar(scen_df["Scenario"], scen_df["Net_Profit_Uplift_INR"]/1000, color=colors_scen, width=0.5)
ax3.axhline(0, color="black", linewidth=0.8)
ax3.set_title("3. Net Profit Uplift Across Sensitivity Scenarios (Rs. '000)\n(Accounts for Immediate Cancels + 30-Day Retention LTV Loss)", fontweight="bold", fontsize=10)
ax3.set_ylabel("Net Profit Uplift (Rs. '000)")
for b in bars:
    ax3.text(b.get_x() + b.get_width()/2, b.get_height() + 0.8, f"+Rs.{b.get_height():.1f}k", ha="center", fontweight="bold", fontsize=9)

# Chart 4
ax4 = fig.add_axes([0.48, 0.08, 0.47, 0.29])
ax4.axis("off")
ax4.set_title("4. Real Data-Driven Checkout Add-Ons (Apriori Engine) & Key Assumptions", fontweight="bold", fontsize=10, loc="left")

top5 = addons_df[["trigger_item", "recommended_addon", "unit_price_inr", "item_profit_inr", "lift"]].head(5).copy()
top5["trigger_item"] = top5["trigger_item"].astype(str).str.slice(0, 22)
top5["recommended_addon"] = top5["recommended_addon"].astype(str).str.slice(0, 22)
top5["lift"] = top5["lift"].round(2)
top5.columns = ["Cart Item", "Suggested Add-On", "Price (Rs.)", "Profit (+Rs.)", "Lift"]

if len(top5) > 0:
    table = ax4.table(cellText=top5.values, colLabels=top5.columns, loc="upper center", cellLoc="center", bbox=[0, 0.32, 1, 0.65])
    table.auto_set_font_size(False); table.set_fontsize(8.5)

assumptions_text = (
    "MODELED ASSUMPTIONS: Margins by Dept (6% Dairy/Staples to 30% Personal Care) | "
    "Fulfillment: Rs.40 Normal (Rs.32 Rider + Rs.8 Pack), Rs.55 Peak (7-10, 18-22) + 1.5% Payment Fee | "
    f"LTV Penalty = Churned Orders x Baseline Avg Order Profit (Rs.{avg_order_profit:.2f})."
)
ax4.text(0, 0.05, assumptions_text, fontsize=8, color="#333333", wrap=True, bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF3CD", edgecolor="#FFEEBA"))

plt.savefig("Blinkit_Executive_Dashboard.png", dpi=300)
plt.close(fig)
print("SUCCESS! Blinkit_Executive_Dashboard.png saved cleanly.")