"""Solaris Dashboard - Real-time GivEnergy telemetry visualization."""

import logging
from dash import Dash, callback, Input, Output, State
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd

from solaris_dashboard.layout import create_layout, create_metric_card
from solaris_dashboard.database import (
    query_summary_1min,
    query_summary_15min,
    query_summary_daily,
    query_state_changes,
    query_freshness_log,
    get_latest_metrics,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

# Set app layout
app.layout = create_layout()


# Callbacks
@app.callback(
    [Output("metrics-row", "children"),
     Output("power-graph", "figure"),
     Output("soc-graph", "figure"),
     Output("energy-graph", "figure"),
     Output("freshness-table", "children"),
     Output("state-changes-table", "children")],
    [Input("interval-component", "n_intervals"),
     Input("btn-1h", "n_clicks"),
     Input("btn-6h", "n_clicks"),
     Input("btn-24h", "n_clicks"),
     Input("btn-7d", "n_clicks"),
     Input("btn-30d", "n_clicks")],
    State("time-range-store", "data"),
    prevent_initial_call=False
)
def update_dashboard(n_intervals, btn_1h, btn_6h, btn_24h, btn_7d, btn_30d, time_range):
    """Update all dashboard components."""
    try:
        # Determine which button was clicked
        from dash import ctx
        if ctx.triggered:
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            if trigger_id == "btn-1h":
                time_range = {"hours": 1, "type": "1min"}
            elif trigger_id == "btn-6h":
                time_range = {"hours": 6, "type": "1min"}
            elif trigger_id == "btn-24h":
                time_range = {"hours": 24, "type": "1min"}
            elif trigger_id == "btn-7d":
                time_range = {"days": 7, "type": "15min"}
            elif trigger_id == "btn-30d":
                time_range = {"days": 30, "type": "daily"}

        # Query data based on time range
        if "hours" in time_range:
            hours = time_range["hours"]
            df = query_summary_1min(hours=hours)
        else:
            days = time_range.get("days", 7)
            if time_range.get("type") == "15min":
                df = query_summary_15min(days=days)
            else:
                df = query_summary_daily(days=days)

        # Get latest metrics
        latest = get_latest_metrics()
        
        # Create metric cards
        metric_cards = []
        for _, row in latest.iterrows():
            if row["metric"] == "pv_power":
                metric_cards.append(
                    create_metric_card("PV Power", row["kw"], "W", "success")
                )
            elif row["metric"] == "battery_power":
                metric_cards.append(
                    create_metric_card("Battery Power", row["kw"], "W", "warning")
                )
            elif row["metric"] == "grid_power":
                metric_cards.append(
                    create_metric_card("Grid Power", row["kw"], "W", "info")
                )
            elif row["metric"] == "soc":
                metric_cards.append(
                    create_metric_card("Battery SOC", row["kw"], "%", "primary")
                )

        # Power graph
        power_df = df[df["metric"].isin(["pv_power", "battery_power", "grid_power"])]
        power_fig = go.Figure()
        for metric in ["pv_power", "battery_power", "grid_power"]:
            data = power_df[power_df["metric"] == metric]
            if not data.empty:
                power_fig.add_trace(
                    go.Scatter(
                        x=data["timestamp"],
                        y=data["kw"],
                        mode="lines",
                        name=metric.replace("_", " ").title(),
                        hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>%{y:.2f}W<extra></extra>"
                    )
                )
        power_fig.update_layout(
            hovermode="x unified",
            margin=dict(l=50, r=20, t=20, b=50),
            template="plotly_white"
        )

        # SOC graph
        soc_df = df[df["metric"] == "soc"]
        soc_fig = go.Figure(
            go.Scatter(
                x=soc_df["timestamp"],
                y=soc_df["kw"],
                mode="lines",
                name="Battery SOC",
                fill="tozeroy",
                line=dict(color="rgb(55, 128, 191)"),
                hovertemplate="<b>Battery SOC</b><br>%{x}<br>%{y:.1f}%<extra></extra>"
            )
        )
        soc_fig.update_layout(
            hovermode="x unified",
            margin=dict(l=50, r=20, t=20, b=50),
            template="plotly_white",
            yaxis=dict(range=[0, 100])
        )

        # Energy graph
        energy_df = df[df["metric"].isin(["pv_power", "battery_power", "grid_power"])]
        energy_fig = go.Figure()
        for metric in ["pv_power", "battery_power", "grid_power"]:
            data = energy_df[energy_df["metric"] == metric].sort_values("timestamp")
            if not data.empty:
                energy_fig.add_trace(
                    go.Scatter(
                        x=data["timestamp"],
                        y=data["cumulative_kwh"],
                        mode="lines",
                        name=f"{metric.replace('_', ' ').title()} (Cumulative)",
                        hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>%{y:.2f}kWh<extra></extra>"
                    )
                )
        energy_fig.update_layout(
            hovermode="x unified",
            margin=dict(l=50, r=20, t=20, b=50),
            template="plotly_white"
        )

        # Freshness table
        freshness_df = query_freshness_log(hours=24)
        freshness_table = dbc.Table.from_dataframe(
            freshness_df.head(10)[["timestamp", "event_type", "max_cache_age_seconds", "message"]],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            size="sm",
            className="text-muted"
        ) if not freshness_df.empty else "No data"

        # State changes table
        state_df = query_state_changes(limit=20)
        state_table = dbc.Table.from_dataframe(
            state_df[["timestamp", "state_key", "state_value"]],
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            size="sm",
            className="text-muted"
        ) if not state_df.empty else "No state changes"

        return metric_cards, power_fig, soc_fig, energy_fig, freshness_table, state_table

    except Exception as e:
        logger.error(f"Dashboard update error: {e}")
        return [], go.Figure(), go.Figure(), go.Figure(), f"Error: {e}", f"Error: {e}"


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8050)
