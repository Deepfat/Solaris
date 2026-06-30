"""Dashboard layout definition."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from solaris_dashboard.database import get_latest_metrics


def create_metric_card(metric_name, value, unit="", color="primary"):
    """Create a metric card."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.H6(metric_name, className="card-title text-muted"),
                html.H3(f"{value:.2f} {unit}", className=f"text-{color}"),
            ]),
            className="mb-3"
        ),
        width=12, md=6, lg=3
    )


def create_layout():
    """Create the main dashboard layout."""
    return dbc.Container(
        fluid=True,
        children=[
            # Header
            dbc.Row(
                dbc.Col([
                    html.H1("⚡ Solaris Dashboard", className="mt-4 mb-2"),
                    html.P("Real-time GivEnergy inverter telemetry", className="text-muted mb-4"),
                ], width=12),
            ),

            # Live Metrics
            dbc.Row(
                dbc.Col([
                    html.H5("📊 Live Metrics (Last 1-Min Read)", className="mb-3"),
                ], width=12),
            ),

            dbc.Row(
                id="metrics-row",
                className="mb-4"
            ),

            # Time Range Selector
            dbc.Row(
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("1H", id="btn-1h", outline=True, color="primary", size="sm", active=True),
                        dbc.Button("6H", id="btn-6h", outline=True, color="primary", size="sm"),
                        dbc.Button("24H", id="btn-24h", outline=True, color="primary", size="sm"),
                        dbc.Button("7D", id="btn-7d", outline=True, color="primary", size="sm"),
                        dbc.Button("30D", id="btn-30d", outline=True, color="primary", size="sm"),
                    ], className="mb-3"),
                ], width=12),
            ),

            # Charts
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Power Output (W)", className="card-title"),
                            dcc.Loading(
                                dcc.Graph(id="power-graph", style={"height": "400px"}),
                                type="default"
                            ),
                        ]),
                    ]),
                ], width=12, lg=6, className="mb-4"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Battery State of Charge (%)", className="card-title"),
                            dcc.Loading(
                                dcc.Graph(id="soc-graph", style={"height": "400px"}),
                                type="default"
                            ),
                        ]),
                    ]),
                ], width=12, lg=6, className="mb-4"),
            ]),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Cumulative Energy (kWh)", className="card-title"),
                            dcc.Loading(
                                dcc.Graph(id="energy-graph", style={"height": "400px"}),
                                type="default"
                            ),
                        ]),
                    ]),
                ], width=12, lg=6, className="mb-4"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Data Freshness", className="card-title"),
                            dcc.Loading(
                                html.Div(id="freshness-table"),
                                type="default"
                            ),
                        ]),
                    ]),
                ], width=12, lg=6, className="mb-4"),
            ]),

            # State Changes
            dbc.Row(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("🔄 Recent State Changes", className="card-title"),
                            dcc.Loading(
                                html.Div(id="state-changes-table"),
                                type="default"
                            ),
                        ]),
                    ]),
                ], width=12, className="mb-4"),
            ),

            # Auto-refresh interval
            dcc.Interval(
                id="interval-component",
                interval=30*1000,  # Update every 30 seconds
                n_intervals=0
            ),

            # Hidden div to store selected time range
            dcc.Store(id="time-range-store", data={"hours": 1, "type": "1min"}),
        ],
        className="py-4"
    )
