
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Color palette
C_PRIMARY    = '#2E86C1'
C_SECONDARY  = '#A23B72'
C_POSITIVE   = '#00D2D3'
C_NEGATIVE   = '#FF6B6B'
C_LIGHT_GREY = '#F8F9FA'

st.set_page_config(layout="wide", page_title="Where Should I Live?")

# Basic styling
st.markdown(
    f"""
    <style>
    .main {{
        background-color: #F8FAFF;
    }}
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 2rem;
    }}
    .stMetric label {{
        font-weight: 600;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_data():
    df = pd.read_csv("df_final_clean.csv")
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    if "City" in df.columns:
        df = df.set_index("City")
    return df

df_final = load_data()

st.title("Where Should I Live?")
st.markdown(
    "An interactive dashboard that uses your own dataset to recommend the best cities "
    "based on your priorities."
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Number of cities", len(df_final))
with col2:
    n_countries = df_final["Country"].nunique() if "Country" in df_final.columns else "N/A"
    st.metric("Number of countries", n_countries)
with col3:
    st.metric("Columns available", len(df_final.columns))

@st.cache_data
def recommend_cities(df, weights, constraints=None):
    df_pro = df.copy()

    if constraints:
        for col, (typ, val) in constraints.items():
            if col in df_pro.columns:
                if typ == "max":
                    df_pro = df_pro[df_pro[col] <= val]
                elif typ == "min":
                    df_pro = df_pro[df_pro[col] >= val]

    if len(df_pro) == 0:
        return None

    # True = higher is better, False = lower is better
    config = {
        "Average Monthly Salary": True,
        "Salary_vs_CostLiv_Diff": True,   # your net income column
        "GDP per Capita": True,
        "Health Care Index": True,
        "Population": True,
        "Unemployment Rate": False,
        "Average Rent Price": False,
        "Average Cost of Living": False,
        "Crime Index": False,
        "Traffic Index": False,
        "Days of very strong heat stress": False,
    }

    df_pro["score"] = 0.0
    total_weight = sum(weights[col] for col in weights if col in df_pro.columns)

    for col, higher_is_better in config.items():
        if col in df_pro.columns and col in weights and weights[col] > 0:
            rank = df_pro[col].rank(pct=True)
            if not higher_is_better:
                rank = 1 - rank
            df_pro["score"] += rank * weights[col]

    if total_weight > 0:
        df_pro["Match %"] = (df_pro["score"] / total_weight * 100).round(1)
    else:
        df_pro["Match %"] = 0.0

    return df_pro.sort_values("Match %", ascending=False)

st.header("Preference weights (0–10)")

weight_options = {
    "Salary_vs_CostLiv_Diff": {
        "label": "Disposable Income",
        "desc": "Difference between salary and cost of living (higher = more money left each month).",
    },
    "Crime Index": {
        "label": "Crime Index",
        "desc": "Overall crime level in the city (lower = safer).",
    },
    "Health Care Index": {
        "label": "Health Care Index",
        "desc": "Quality and accessibility of healthcare services (higher = better).",
    },
    "Average Monthly Salary": {
        "label": "Average Monthly Salary",
        "desc": "Average gross monthly salary in the city (higher = better).",
    },
    "GDP per Capita": {
        "label": "GDP per Capita",
        "desc": "Economic development level of the country (higher = wealthier).",
    },
    "Population": {
        "label": "Population",
        "desc": "Total city population (higher = larger city, more services and opportunities).",
    },
    "Unemployment Rate": {
        "label": "Unemployment Rate",
        "desc": "Percentage of people without jobs (lower = more job security).",
    },
    "Average Rent Price": {
        "label": "Average Rent Price",
        "desc": "Average monthly rent (lower = more affordable housing).",
    },
    "Average Cost of Living": {
        "label": "Average Cost of Living",
        "desc": "Average monthly cost for basic expenses (lower = cheaper to live).",
    },
    "Traffic Index": {
        "label": "Traffic Index",
        "desc": "Traffic congestion and travel time (lower = faster commuting).",
    },
    "Days of very strong heat stress": {
        "label": "Days of very strong heat stress",
        "desc": "Number of extremely hot days (lower = more climate comfort).",
    },
}

weights = {}
for col, meta in weight_options.items():
    if col in df_final.columns:
        st.markdown(f"**{meta['label']}**")
        st.caption(meta["desc"])
        weights[col] = st.slider(
            f"Weight for {col}",
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key=f"w_{col}",
        )

st.header("Hard filters (optional)")

constraint_cols = st.columns(3)
constraints = {}
for idx, (col, meta) in enumerate(weight_options.items()):
    if col in df_final.columns:
        with constraint_cols[idx % 3]:
            choice = st.selectbox(
                f"Filter on {meta['label']}",
                ["None", "Maximum", "Minimum"],
                key=f"filter_{col}",
            )
            if choice != "None":
                mn = float(df_final[col].min())
                mx = float(df_final[col].max())
                default_val = (mn + mx) / 2
                val = st.number_input(
                    f"{choice} allowed for {col}",
                    min_value=mn,
                    max_value=mx,
                    value=default_val,
                    key=f"filter_value_{col}",
                )
                constraints[col] = ("max" if choice == "Maximum" else "min", val)

st.markdown("---")

if st.button("Compute Top 5 cities", type="primary", use_container_width=True):
    result = recommend_cities(df_final, weights, constraints)

    if result is not None and len(result) > 0:
        st.success("Top 5 cities calculated based on your preferences.")

        top5 = result[["Country", "Match %"]].head(5)
        top5.index.name = "City"

        st.subheader("Top 5 cities")
        st.dataframe(
            top5.style.format({"Match %": "{:.1f}%"}),
            use_container_width=True,
        )

        top5_plot = result.head(5).reset_index()  # City, Country, Match %

        st.subheader("Podium")
        c1, c2, c3 = st.columns(3)
        c1.metric("1st", top5_plot.iloc[0]["City"], f"{top5_plot.iloc[0]['Match %']:.1f}%")
        if len(top5_plot) > 1:
            c2.metric("2nd", top5_plot.iloc[1]["City"], f"{top5_plot.iloc[1]['Match %']:.1f}%")
        if len(top5_plot) > 2:
            c3.metric("3rd", top5_plot.iloc[2]["City"], f"{top5_plot.iloc[2]['Match %']:.1f}%")

        st.subheader("Overall suitability score (%)")
        fig1 = px.bar(
            top5_plot,
            x="Match %",
            y="City",
            orientation="h",
            color="Match %",
            text="Match %",
            color_continuous_scale=[C_NEGATIVE, C_SECONDARY, C_POSITIVE],
        )
        fig1.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig1.update_layout(
            xaxis_title="Match to your preferences (%)",
            yaxis_title="City",
            height=400,
            plot_bgcolor="white",
        )
        st.plotly_chart(fig1, use_container_width=True)

        economic_cols = [
            "Average Monthly Salary",
            "Average Cost of Living",
            "Average Rent Price",
            "Salary_vs_CostLiv_Diff",
        ]
        available_econ = [c for c in economic_cols if c in df_final.columns]
        if available_econ:
            st.subheader("Economic profile of Top 5 cities")
            econ = top5_plot[["City"] + available_econ].melt(
                id_vars="City", var_name="Metric", value_name="Value"
            )
            econ_palette = {
                "Average Monthly Salary": C_PRIMARY,
                "Average Cost of Living": C_NEGATIVE,
                "Average Rent Price": C_SECONDARY,
                "Salary_vs_CostLiv_Diff": C_POSITIVE,
            }
            fig2 = px.bar(
                econ,
                x="City",
                y="Value",
                color="Metric",
                barmode="group",
                color_discrete_map=econ_palette,
            )
            fig2.update_layout(
                xaxis_title="City",
                yaxis_title="Amount (same currency as your dataset)",
                height=450,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig2, use_container_width=True)

        risk_cols = ["Crime Index", "Unemployment Rate", "Traffic Index"]
        available_risk = [c for c in risk_cols if c in df_final.columns]
        if available_risk:
            st.subheader("Safety and mobility indicators")
            risk = top5_plot[["City"] + available_risk].melt(
                id_vars="City", var_name="Metric", value_name="Value"
            )
            risk_palette = {
                "Crime Index": C_NEGATIVE,
                "Unemployment Rate": C_SECONDARY,
                "Traffic Index": C_LIGHT_GREY,
            }
            fig3 = px.bar(
                risk,
                x="City",
                y="Value",
                color="Metric",
                barmode="group",
                color_discrete_map=risk_palette,
            )
            fig3.update_layout(
                xaxis_title="City",
                yaxis_title="Index / percentage (original units)",
                height=450,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig3, use_container_width=True)

        active_cols = [
            c for c in weight_options
            if c in df_final.columns and weights.get(c, 0) > 0
        ]
        if len(active_cols) >= 3:
            st.subheader("Normalized comparison across active criteria (0–100%)")

            top5_radar = top5_plot[["City"] + active_cols].copy()

            config_for_radar = {
                "Average Monthly Salary": True,
                "Salary_vs_CostLiv_Diff": True,
                "GDP per Capita": True,
                "Health Care Index": True,
                "Population": True,
                "Unemployment Rate": False,
                "Average Rent Price": False,
                "Average Cost of Living": False,
                "Crime Index": False,
                "Traffic Index": False,
                "Days of very strong heat stress": False,
            }

            for col in active_cols:
                higher_is_better = config_for_radar.get(col, True)
                ranks = top5_radar[col].rank(pct=True)
                if not higher_is_better:
                    ranks = 1 - ranks
                top5_radar[col] = (ranks * 100).round(1)

            fig_r = go.Figure()
            radar_colors = [C_PRIMARY, C_SECONDARY, C_POSITIVE, C_NEGATIVE, "#74B9FF"]
            for i, (_, row) in enumerate(top5_radar.iterrows()):
                fig_r.add_trace(
                    go.Scatterpolar(
                        r=[row[c] for c in active_cols],
                        theta=active_cols,
                        fill="toself",
                        name=row["City"],
                        line_color=radar_colors[i % len(radar_colors)],
                    )
                )

            fig_r.update_layout(
                polar=dict(
                    radialaxis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100])
                ),
                showlegend=True,
                height=500,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig_r, use_container_width=True)

    else:
        st.warning("No city satisfies your filters. Try relaxing some constraints or weights.")
