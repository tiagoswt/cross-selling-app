import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import itertools
from datetime import datetime

# Set page config
st.set_page_config(page_title="Brand-Country Analysis Dashboard", layout="wide")

# File uploader to load CSV or Excel file
uploaded_file = st.sidebar.file_uploader(
    "Upload your CSV or Excel file", type=["csv", "xlsx"]
)


# Load the data
@st.cache_data(show_spinner=False)
def load_data(file):
    if file is not None:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
        df["brands"] = (
            df["brands"].str.split(",").apply(lambda x: list(set(x)))
        )  # Remove duplicate brands per order
        df["orderDate"] = pd.to_datetime(
            df["orderDate"]
        ).dt.date  # Convert to date, remove time
        return df
    else:
        return None


df = load_data(uploaded_file)

if df is not None:
    # Get the list of available countries from the data
    available_countries = sorted(
        df["shipCountryCode"].unique().tolist(), key=lambda x: str(x)
    )
    available_countries.insert(0, "All Countries")  # Add an option for "All Countries"

    st.title("Brand-Country Analysis Dashboard")

    # Sidebar for selecting analysis
    analysis = st.sidebar.selectbox(
        "Choose an analysis",
        [
            "Country Diversity",
            "Brand Popularity",
            "Brand Exclusivity",
            "Brand Co-occurrence",
            "Co-occurrence by Brand",
        ],
    )

    # Create a dropdown for country selection
    selected_country = st.sidebar.selectbox(
        "Select a country", options=available_countries
    )

    # Date filter selection
    min_date, max_date = df["orderDate"].min(), df["orderDate"].max()
    start_date, end_date = st.sidebar.date_input(
        "Select Date Range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )

    # Filter the dataset by selected country (if not "All Countries")
    df_filtered = df[(df["orderDate"] >= start_date) & (df["orderDate"] <= end_date)]
    if selected_country != "All Countries":
        df_filtered = df_filtered[df_filtered["shipCountryCode"] == selected_country]

    # Display filtered data and metrics
    st.subheader(f"Metrics for {selected_country}")

    # Overall Metrics for the selected country
    st.sidebar.header(f"Metrics for {selected_country}")
    st.sidebar.metric("Total Orders", len(df_filtered))
    st.sidebar.metric(
        "Total Brands",
        len(set(brand for brands in df_filtered["brands"] for brand in brands)),
    )

    # Define explanations for each analysis
    analysis_explanations = {
        "Brand Popularity": "This analysis shows the most popular brands by counting the number of orders that contain each brand.",
        "Country Diversity": "This analysis shows the diversity of brands in each country, counting how many unique brands are ordered in each region.",
        "Brand Penetration": "This analysis shows how often each brand appears in orders across different countries, expressed as a percentage of total orders.",
        "Brand Co-occurrence": "This analysis shows how frequently specific brands are purchased together in the same order, highlighting potential product pairings.",
        "Brand Exclusivity": "This analysis shows how often customers purchase only one brand in their order, indicating brand loyalty or specialization.",
        "Co-occurrence by Brand": "This analysis allows you to select a specific brand and see how often it co-occurs with other brands, either as a percentage or as a total count.",
    }

    # Display the explanation for the selected analysis
    st.markdown(f"**Explanation:** {analysis_explanations[analysis]}")

    # Helper function to plot bar charts
    def plot_bar_chart(data, title, xlabel, ylabel):
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x=data.index, y=data.values, ax=ax)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=45)
        for p in ax.patches:
            ax.annotate(
                format(p.get_height(), ".1f"),
                (p.get_x() + p.get_width() / 2.0, p.get_height()),
                ha="center",
                va="center",
                xytext=(0, 9),
                textcoords="offset points",
            )
        st.pyplot(fig)

    # Brand Popularity
    if analysis == "Brand Popularity":
        st.header(f"Brand Popularity in {selected_country}")
        top_n = st.slider("Select top N brands", 5, 20, 10)
        analysis_type = st.radio(
            "Choose the type of analysis", ("Total Value", "Percentage")
        )

        brand_popularity = (
            df_filtered.explode("brands")["brands"].value_counts().head(top_n)
        )

        if analysis_type == "Percentage":
            total_orders = len(df_filtered)
            brand_popularity = (brand_popularity / total_orders) * 100
            ylabel = "Percentage of Orders"
        else:
            ylabel = "Number of Orders"

        plot_bar_chart(
            brand_popularity,
            f"Top {top_n} Most Popular Brands in {selected_country}",
            "Brand",
            ylabel,
        )

    # Country Diversity
    if analysis == "Country Diversity":
        st.header(f"Brand Diversity in {selected_country}")
        top_n = st.slider("Select top N countries", 5, 20, 10)

        country_diversity = df_filtered.groupby("shipCountryCode")["brands"].apply(
            lambda x: len(set(brand for brands in x for brand in brands))
        )
        country_diversity_sorted = country_diversity.sort_values(ascending=False).head(
            top_n
        )

        plot_bar_chart(
            country_diversity_sorted,
            f"Top {top_n} Countries by Brand Diversity",
            "Country",
            "Number of Unique Brands",
        )

    # Brand Co-occurrence
    if analysis == "Brand Co-occurrence":
        st.header(f"Brand Co-occurrence in {selected_country}")

        df_exploded = df_filtered.explode("brands")
        top_n = st.slider("Select top N brands", 5, 50, 20)
        analysis_type = st.radio(
            "Choose the type of analysis", ("Total Value", "Percentage")
        )

        top_brands = df_exploded["brands"].value_counts().head(top_n).index.tolist()
        df_top_brands = df_filtered[
            df_filtered["brands"].apply(
                lambda x: any(brand in top_brands for brand in x)
            )
        ]

        co_occurrence_dict = {
            brand: {brand: 0 for brand in top_brands} for brand in top_brands
        }

        for brands_list in df_top_brands["brands"]:
            relevant_brands = [brand for brand in brands_list if brand in top_brands]
            for brand_a, brand_b in itertools.combinations(relevant_brands, 2):
                co_occurrence_dict[brand_a][brand_b] += 1
                co_occurrence_dict[brand_b][brand_a] += 1

        co_occurrence_df = pd.DataFrame(co_occurrence_dict)
        co_occurrence_df = co_occurrence_df.loc[
            ~(co_occurrence_df == 0).all(axis=1), ~(co_occurrence_df == 0).all(axis=0)
        ]

        if analysis_type == "Percentage":
            total_occurrences = co_occurrence_df.values.sum()
            co_occurrence_df = (co_occurrence_df / total_occurrences) * 100
            fmt = ".2f"
            ylabel = "Percentage of Co-occurrences"
        else:
            fmt = "d"
            ylabel = "Total Co-occurrences"

        fig, ax = plt.subplots(figsize=(12, 10))
        sns.heatmap(co_occurrence_df, cmap="YlGnBu", annot=True, fmt=fmt, ax=ax)
        ax.set_title(f"Brand Co-occurrence (Top {top_n} Brands) in {selected_country}")
        ax.set_xlabel("Brand")
        ax.set_ylabel("Brand")
        st.pyplot(fig)

    # Brand Exclusivity
    if analysis == "Brand Exclusivity":
        st.header(f"Brand Exclusivity in {selected_country}")
        top_n = st.slider("Select top N brands", 5, 20, 10)
        analysis_type = st.radio(
            "Choose the type of analysis", ("Total Value", "Percentage")
        )

        single_brand_orders = df_filtered[df_filtered["brands"].apply(len) == 1]
        brand_exclusivity = (
            single_brand_orders["brands"]
            .apply(lambda x: x[0])
            .value_counts()
            .head(top_n)
        )

        if analysis_type == "Percentage":
            total_orders = len(df_filtered)
            brand_exclusivity = (brand_exclusivity / total_orders) * 100
            ylabel = "Percentage of Single-Brand Orders"
        else:
            ylabel = "Total Single-Brand Orders"

        plot_bar_chart(
            brand_exclusivity,
            f"Top {top_n} Brands by Exclusivity (Single-Brand Orders) in {selected_country}",
            "Brand",
            ylabel,
        )

    # Co-occurrence by Brand
    if analysis == "Co-occurrence by Brand":
        st.header(f"Co-occurrence by Brand in {selected_country}")

        selected_brand = st.selectbox(
            "Select a brand to analyze its co-occurrence with other brands",
            options=sorted(
                df_filtered.explode("brands")["brands"].unique(), key=lambda x: str(x)
            ),
            index=0,
        )
        top_n = st.slider("Select top N brands for co-occurrence analysis", 5, 50, 20)
        analysis_type = st.radio(
            "Choose the type of analysis", ("Percentage", "Total Value")
        )

        df_filtered_brand = df_filtered[
            df_filtered["brands"].apply(lambda x: selected_brand in x)
        ]

        co_occurrence_count = {
            brand: 0
            for brand in df_filtered.explode("brands")["brands"].unique()
            if brand != selected_brand
        }

        for brands_list in df_filtered_brand["brands"]:
            for brand in brands_list:
                if brand != selected_brand:
                    co_occurrence_count[brand] += 1

        co_occurrence_count = {
            brand: count for brand, count in co_occurrence_count.items() if count > 0
        }

        co_occurrence_df = pd.DataFrame(
            list(co_occurrence_count.items()), columns=["Brand", "Count"]
        ).nlargest(top_n, columns="Count")

        if analysis_type == "Percentage":
            total_co_occurrences = sum(co_occurrence_count.values())
            co_occurrence_df["Percentage"] = (
                co_occurrence_df["Count"] / total_co_occurrences
            ) * 100
            co_occurrence_df = co_occurrence_df.sort_values(
                by="Percentage", ascending=False
            )
            y_label = "Percentage of Co-occurrence"
            y_values = co_occurrence_df["Percentage"]
        else:
            co_occurrence_df = co_occurrence_df.sort_values(by="Count", ascending=False)
            y_label = "Total Co-occurrence Count"
            y_values = co_occurrence_df["Count"]

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x=co_occurrence_df["Brand"], y=y_values, ax=ax)
        for p in ax.patches:
            ax.annotate(
                format(p.get_height(), ".1f"),
                (p.get_x() + p.get_width() / 2.0, p.get_height()),
                ha="center",
                va="center",
                xytext=(0, 9),
                textcoords="offset points",
            )
        st.pyplot(fig)

    # Footer and Sidebar explanations
    st.sidebar.markdown(
        """
    ## How to use this dashboard

    1. Use the dropdown menu to select a country, date range, and analysis.
    2. The charts update automatically based on your selections.
    3. Overall metrics for the selected country are shown in the sidebar.

    This dashboard helps analyze relationships between brands and countries in your order data.
    """
    )

    # Footer
    st.markdown("---")
    st.markdown("Created with Streamlit by Sweetcare")
else:
    st.warning(
        "No data available. Please upload a valid CSV or Excel file.",
        icon=":material/warning:",
    )

