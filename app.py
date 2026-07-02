from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)


def load_data():
    df = pd.read_excel("Amazon_Sales.xlsx")
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    return df


def _series_to_chart(series):
    return {
        "labels": series.index.astype(str).tolist(),
        "values": [round(float(v), 2) for v in series.values.tolist()],
    }


def _format_rows(df):
    # Keep the table practical and fast by limiting to latest 220 rows.
    rows = []
    view_df = df.sort_values("Order Date", ascending=False).head(220)
    for _, row in view_df.iterrows():
        rows.append(
            {
                "order_id": str(row.get("Order ID", "")),
                "order_date": row["Order Date"].strftime("%Y-%m-%d")
                if pd.notnull(row.get("Order Date"))
                else "",
                "state": str(row.get("State", "")),
                "city": str(row.get("City", "")),
                "category": str(row.get("Category", "")),
                "sub_category": str(row.get("Sub-Category", "")),
                "product": str(row.get("Product Name", "")),
                "customer": str(row.get("Customer Name", "")),
                "payment_mode": str(row.get("Payment Mode", "")),
                "quantity": int(row.get("Quantity", 0)),
                "sales": round(float(row.get("Sales", 0.0)), 2),
                "profit": round(float(row.get("Profit", 0.0)), 2),
            }
        )
    return rows


def build_dashboard_data(df):
    total_sales = float(df["Sales"].sum())
    total_profit = float(df["Profit"].sum())
    total_orders = int(df["Order ID"].nunique())
    avg_sales = float(df["Sales"].mean())
    avg_profit = float(df["Profit"].mean())
    profit_margin = (total_profit / total_sales * 100) if total_sales else 0

    sales_by_state = df.groupby("State")["Sales"].sum().sort_values(ascending=False)
    sales_by_category = df.groupby("Category")["Sales"].sum().sort_values(ascending=False)
    profit_by_category = df.groupby("Category")["Profit"].sum().sort_values(ascending=False)
    payment_mode_orders = (
        df.groupby("Payment Mode")["Order ID"].nunique().sort_values(ascending=False)
    )

    monthly = (
        df.groupby(df["Order Date"].dt.to_period("M"))
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        .sort_index()
    )
    monthly.index = monthly.index.astype(str)

    top_products = (
        df.groupby("Product Name")["Sales"].sum().nlargest(10).sort_values(ascending=True)
    )
    top_customers = (
        df.groupby("Customer Name")["Sales"].sum().sort_values(ascending=False).head(5)
    )
    risky_products = (
        df[df["Sales"] > df["Sales"].quantile(0.7)]
        .sort_values("Profit")
        .head(8)[["Product Name", "Category", "Sales", "Profit"]]
    )

    best_sales_month = monthly["Sales"].idxmax()
    best_profit_month = monthly["Profit"].idxmax()

    return {
        "kpis": {
            "total_sales": f"{total_sales:,.2f}",
            "total_profit": f"{total_profit:,.2f}",
            "total_orders": f"{total_orders}",
            "avg_sales": f"{avg_sales:,.2f}",
            "avg_profit": f"{avg_profit:,.2f}",
            "profit_margin": f"{profit_margin:.2f}%",
        },
        "insights": {
            "best_state": f"{sales_by_state.index[0]} ({sales_by_state.iloc[0]:,.2f})",
            "weak_state": f"{sales_by_state.index[-1]} ({sales_by_state.iloc[-1]:,.2f})",
            "best_sales_month": f"{best_sales_month} ({monthly.loc[best_sales_month, 'Sales']:,.2f})",
            "best_profit_month": f"{best_profit_month} ({monthly.loc[best_profit_month, 'Profit']:,.2f})",
            "top_payment": f"{payment_mode_orders.index[0]} ({int(payment_mode_orders.iloc[0])} orders)",
        },
        "sales_by_state": _series_to_chart(sales_by_state),
        "sales_by_category": _series_to_chart(sales_by_category),
        "profit_by_category": _series_to_chart(profit_by_category),
        "payment_mode_orders": _series_to_chart(payment_mode_orders),
        "monthly_sales": {
            "labels": monthly.index.tolist(),
            "sales": [round(float(v), 2) for v in monthly["Sales"].tolist()],
            "profit": [round(float(v), 2) for v in monthly["Profit"].tolist()],
        },
        "top_products": _series_to_chart(top_products),
        "top_customers": [
            {"name": i, "sales": round(float(v), 2)} for i, v in top_customers.items()
        ],
        "risky_products": [
            {
                "product": str(row["Product Name"]),
                "category": str(row["Category"]),
                "sales": round(float(row["Sales"]), 2),
                "profit": round(float(row["Profit"]), 2),
            }
            for _, row in risky_products.iterrows()
        ],
        "table_rows": _format_rows(df),
        "filters": {
            "states": sorted(df["State"].dropna().astype(str).unique().tolist()),
            "categories": sorted(df["Category"].dropna().astype(str).unique().tolist()),
            "payment_modes": sorted(
                df["Payment Mode"].dropna().astype(str).unique().tolist()
            ),
        },
    }


@app.route("/")
def index():
    df = load_data()
    dashboard = build_dashboard_data(df)
    return render_template("index.html", dashboard=dashboard)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
