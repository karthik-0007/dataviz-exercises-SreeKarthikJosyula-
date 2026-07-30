"""Lecture 10 assignment: interactive CO₂ emissions dashboard.

Run from the week10 folder with:
    streamlit run lecture10_exercise.py
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CO₂ Emissions Explorer", page_icon="🌍", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load and validate the course CO₂ dataset."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / "data" / "co2_emissions.csv",
        script_dir.parent / "data" / "co2_emissions.csv",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        raise FileNotFoundError(
            "co2_emissions.csv was not found. Put it in week10/data/ or the repo data/ folder."
        )

    df = pd.read_csv(path)
    required = {"Country", "Region", "Year", "CO2_Mt", "CO2_per_capita"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    df = df.copy()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["CO2_Mt"] = pd.to_numeric(df["CO2_Mt"], errors="coerce")
    df["CO2_per_capita"] = pd.to_numeric(df["CO2_per_capita"], errors="coerce")
    df = df.dropna(subset=["Country", "Region", "Year", "CO2_Mt", "CO2_per_capita"])
    df["Year"] = df["Year"].astype(int)
    df["Date"] = pd.to_datetime(df["Year"].astype(str) + "-01-01")
    return df.sort_values(["Country", "Year"]).reset_index(drop=True)


df = load_data()
min_year, max_year = int(df["Year"].min()), int(df["Year"].max())

st.title("Which countries are driving CO₂ emissions?")
st.caption("Use the sidebar to compare regions, countries, time periods, and metrics.")

with st.sidebar:
    st.header("Filters")

    # Widget 1 — selectbox; chained filter parent.
    regions = ["All regions"] + sorted(df["Region"].dropna().unique().tolist())
    selected_region = st.selectbox("Region", regions)

    if selected_region == "All regions":
        country_options = sorted(df["Country"].unique().tolist())
    else:
        country_options = sorted(
            df.loc[df["Region"] == selected_region, "Country"].unique().tolist()
        )

    preferred = ["China", "United States", "India", "Germany"]
    defaults = [country for country in preferred if country in country_options]
    if not defaults:
        defaults = country_options[: min(4, len(country_options))]

    # Widget 2 — multiselect; options are narrowed by the selected region.
    selected_countries = st.multiselect(
        "Countries", options=country_options, default=defaults
    )
    if not selected_countries:
        st.warning("Select at least one country.")
        st.stop()

    # Widget 3 — numeric range slider.
    year_range = st.slider(
        "Year range", min_year, max_year, value=(min_year, max_year)
    )

    # Widget 4 — date input. It is converted to pd.Timestamp before filtering.
    date_range = st.date_input(
        "Calendar date range",
        value=(dt.date(min_year, 1, 1), dt.date(max_year, 1, 1)),
        min_value=dt.date(min_year, 1, 1),
        max_value=dt.date(max_year, 1, 1),
        format="YYYY-MM-DD",
    )
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.warning("Select both a start date and an end date.")
        st.stop()

    # Widget 5 — mutually exclusive metric choice.
    metric = st.radio("Metric", ["Total CO₂ (Mt)", "CO₂ per capita"])

    # Extra widget — controls whether the supporting ranking is displayed.
    show_ranking = st.checkbox("Show latest-year ranking", value=True)

start_ts, end_ts = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
if start_ts > end_ts:
    st.warning("The start date must be before the end date.")
    st.stop()

filtered = df[
    df["Country"].isin(selected_countries)
    & df["Year"].between(year_range[0], year_range[1])
    & df["Date"].between(start_ts, end_ts)
].copy()

if filtered.empty:
    st.warning("No records match the current filters.")
    st.stop()

y_col = "CO2_Mt" if metric == "Total CO₂ (Mt)" else "CO2_per_capita"
y_label = "CO₂ emissions (Mt)" if y_col == "CO2_Mt" else "CO₂ per capita"

# A separate highlight choice avoids giving equal visual weight to every line.
highlight_country = st.selectbox(
    "Country to highlight", selected_countries, index=0
)

st.caption(
    f"Showing {filtered['Country'].nunique()} countries and {len(filtered):,} records | "
    f"Region: {selected_region} | Years: {filtered['Year'].min()}–{filtered['Year'].max()}"
)

latest_year = int(filtered["Year"].max())
latest = filtered[filtered["Year"] == latest_year].copy()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Countries", filtered["Country"].nunique())
k2.metric("Records", f"{len(filtered):,}")
k3.metric(
    f"Highest in {latest_year}",
    latest.loc[latest[y_col].idxmax(), "Country"],
)
k4.metric(
    f"{highlight_country} in {latest_year}",
    f"{latest.loc[latest['Country'] == highlight_country, y_col].iloc[0]:,.2f}"
    if highlight_country in latest["Country"].values
    else "No record",
)

st.divider()

# BBD HIGHLIGHT colour: selected country is blue; comparison countries are grey.
# Countries remain separate line groups even though the comparison lines share a colour.
plot_df = filtered.copy()
plot_df["highlight"] = plot_df["Country"].where(
    plot_df["Country"] == highlight_country, "Other countries"
)

fig = px.line(
    plot_df,
    x="Date",
    y=y_col,
    color="highlight",
    line_group="Country",
    hover_name="Country",
    color_discrete_map={highlight_country: "#2E75B6", "Other countries": "#B7B7B7"},
    category_orders={"highlight": ["Other countries", highlight_country]},
    labels={y_col: y_label, "Date": "", "highlight": ""},
    title=f"{highlight_country} stands out against the selected comparison group",
    height=560,
)
fig.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=12),
    yaxis=dict(gridcolor="#EEEEEE"),
    xaxis=dict(showgrid=False),
    legend=dict(orientation="h", y=1.08),
)
st.plotly_chart(fig, use_container_width=True)

if show_ranking:
    st.subheader(f"How do the selected countries rank in {latest_year}?")
    ranking = latest.sort_values(y_col, ascending=True).copy()
    ranking["highlight"] = ranking["Country"].where(
        ranking["Country"] == highlight_country, "Other countries"
    )
    # BBD HIGHLIGHT colour: blue vs grey, not red vs green.
    rank_fig = px.bar(
        ranking,
        x=y_col,
        y="Country",
        orientation="h",
        color="highlight",
        color_discrete_map={highlight_country: "#2E75B6", "Other countries": "#B7B7B7"},
        labels={y_col: y_label, "Country": "", "highlight": ""},
        title=f"{highlight_country} compared with the latest available values",
        height=max(360, 55 * len(ranking)),
    )
    rank_fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        showlegend=False,
        xaxis=dict(gridcolor="#EEEEEE"),
        yaxis=dict(showgrid=False),
    )
    rank_fig.update_traces(marker_line_width=0)
    st.plotly_chart(rank_fig, use_container_width=True)

with st.expander("Show filtered data"):
    st.dataframe(
        filtered[["Country", "Region", "Year", "CO2_Mt", "CO2_per_capita"]],
        use_container_width=True,
    )
