import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import itertools

# Set page config
st.set_page_config(page_title="Brand-Country Analysis Dashboard", layout="wide")


# Load the data
@st.cache_data
def load_data():
    df = pd.read_csv("cross_selling_test_data.csv")
    df["brands"] = df["brands"].str.split(",")
    return df


df = load_data()

# Get the list of available countries from the data
available_countries = df["shipCountryCode"].unique().tolist()
available_countries.insert(0, "All Countries")  # Add an option for "All Countries"

st.title("Brand-Country Analysis Dashboard")

# Sidebar for selecting analysis
analysis = st.sidebar.selectbox(
    "Choose an analysis",
    [
        "Brand Popularity",
        "Country Diversity",
        "Brand Penetration",
        "Average Basket Size",
        "Brand Co-occurrence",
        "Brand Exclusivity",
    ],
)

# Create a dropdown for country selection
selected_country = st.sidebar.selectbox("Select a country", options=available_countries)

# Filter the dataset by selected country (if not "All Countries")
if selected_country != "All Countries":
    df_filtered = df[df["shipCountryCode"] == selected_country]
else:
    df_filtered = df  # Show data for all countries if "All Countries" is selected

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
    "Average Basket Size": "This analysis shows the average number of brands purchased per order in each country, indicating how many brands customers tend to buy together.",
    "Brand Co-occurrence": "This analysis shows how frequently specific brands are purchased together in the same order, highlighting potential product pairings.",
    "Brand Exclusivity": "This analysis shows how often customers purchase only one brand in their order, indicating brand loyalty or specialization.",
}

# Display the explanation for the selected analysis
st.markdown(f"**Explanation:** {analysis_explanations[analysis]}")

# Brand Popularity
if analysis == "Brand Popularity":
    st.header(f"Brand Popularity in {selected_country}")
    top_n = st.slider("Select top N brands", 5, 20, 10)

    fig, ax = plt.subplots(figsize=(12, 6))
    brand_popularity = (
        df_filtered.explode("brands")["brands"].value_counts().head(top_n)
    )
    sns.barplot(x=brand_popularity.index, y=brand_popularity.values, ax=ax)
    ax.set_title(f"Top {top_n} Most Popular Brands in {selected_country}")
    ax.set_xlabel("Brand")
    ax.set_ylabel("Number of Orders")
    ax.tick_params(axis="x", rotation=45)
    st.pyplot(fig)

# Country Diversity
if analysis == "Country Diversity":
    st.header(f"Brand Diversity in {selected_country}")
    top_n = st.slider("Select top N countries", 5, 20, 10)

    fig, ax = plt.subplots(figsize=(12, 6))
    country_diversity = df_filtered.groupby("shipCountryCode")["brands"].apply(
        lambda x: len(set(brand for brands in x for brand in brands))
    )
    country_diversity_sorted = country_diversity.sort_values(ascending=False).head(
        top_n
    )
    sns.barplot(
        x=country_diversity_sorted.index, y=country_diversity_sorted.values, ax=ax
    )
    ax.set_title(f"Top {top_n} Countries by Brand Diversity in {selected_country}")
    ax.set_xlabel("Country")
    ax.set_ylabel("Number of Unique Brands")
    ax.tick_params(axis="x", rotation=45)
    st.pyplot(fig)

# Brand Penetration
if analysis == "Brand Penetration":
    st.header(f"Brand Penetration in {selected_country}")

    fig, ax = plt.subplots(figsize=(12, 8))
    brand_penetration = (
        df_filtered.explode("brands")
        .groupby("shipCountryCode")["brands"]
        .value_counts(normalize=True)
        .unstack()
        .fillna(0)
    )
    sns.heatmap(brand_penetration, ax=ax, cmap="YlOrRd")
    ax.set_title(f"Brand Penetration by Country in {selected_country}")
    ax.set_xlabel("Brand")
    ax.set_ylabel("Country")
    st.pyplot(fig)

# Average Basket Size
if analysis == "Average Basket Size":
    st.header(f"Average Basket Size in {selected_country}")
    top_n = st.slider("Select top N countries", 5, 20, 10)

    fig, ax = plt.subplots(figsize=(12, 6))
    avg_basket_size = df_filtered.groupby("shipCountryCode")["brands"].apply(
        lambda x: sum(len(brands) for brands in x) / len(x)
    )
    avg_basket_size_sorted = avg_basket_size.sort_values(ascending=False).head(top_n)
    sns.barplot(x=avg_basket_size_sorted.index, y=avg_basket_size_sorted.values, ax=ax)
    ax.set_title(f"Top {top_n} Countries by Average Basket Size in {selected_country}")
    ax.set_xlabel("Country")
    ax.set_ylabel("Average Number of Brands per Order")
    ax.tick_params(axis="x", rotation=45)
    st.pyplot(fig)

# Brand Co-occurrence
if analysis == "Brand Co-occurrence":
    st.header(f"Brand Co-occurrence in {selected_country}")

    # Explode the 'brands' column so each brand in an order gets its own row
    df_exploded = df_filtered.explode("brands")

    # Get the top 20 brands to limit the size of the co-occurrence matrix
    top_brands = df_exploded["brands"].value_counts().head(20).index.tolist()

    # Filter to only orders that include these top brands
    df_top_brands = df_filtered[
        df_filtered["brands"].apply(lambda x: any(brand in top_brands for brand in x))
    ]

    # Initialize a dictionary to hold co-occurrence counts
    co_occurrence_dict = {
        brand: {brand: 0 for brand in top_brands} for brand in top_brands
    }

    # Iterate through each order and compute brand pairs
    for brands_list in df_top_brands["brands"]:
        # Filter the brands in the order to include only top brands
        relevant_brands = [brand for brand in brands_list if brand in top_brands]

        # Get all unique pairs of brands from the order
        for brand_a, brand_b in itertools.combinations(relevant_brands, 2):
            # Increment both [brand_a][brand_b] and [brand_b][brand_a] for co-occurrence
            co_occurrence_dict[brand_a][brand_b] += 1
            co_occurrence_dict[brand_b][brand_a] += 1

    # Convert the co-occurrence dictionary to a DataFrame
    co_occurrence_df = pd.DataFrame(co_occurrence_dict)

    # Plot the co-occurrence matrix
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(co_occurrence_df, cmap="YlGnBu", annot=True, fmt="d", ax=ax)
    ax.set_title(f"Brand Co-occurrence (Top 20 Brands) in {selected_country}")
    ax.set_xlabel("Brand")
    ax.set_ylabel("Brand")
    st.pyplot(fig)

# Brand Exclusivity
if analysis == "Brand Exclusivity":
    st.header(f"Brand Exclusivity in {selected_country}")
    top_n = st.slider("Select top N brands", 5, 20, 10)

    fig, ax = plt.subplots(figsize=(12, 6))
    single_brand_orders = df_filtered[df_filtered["brands"].apply(len) == 1]
    brand_exclusivity = (
        single_brand_orders["brands"]
        .apply(lambda x: x[0])
        .value_counts(normalize=True)
        .head(top_n)
    )
    sns.barplot(x=brand_exclusivity.index, y=brand_exclusivity.values, ax=ax)
    ax.set_title(
        f"Top {top_n} Brands by Exclusivity (Single-Brand Orders) in {selected_country}"
    )
    ax.set_xlabel("Brand")
    ax.set_ylabel("Percentage of Single-Brand Orders")
    ax.tick_params(axis="x", rotation=45)
    st.pyplot(fig)

    # Footer and Sidebar explanations
st.sidebar.markdown(
    """
## How to use this dashboard

1. Use the dropdown menu to select a country and analysis.
2. The charts update automatically based on your selections.
3. Overall metrics for the selected country are shown in the sidebar.

This dashboard helps analyze relationships between brands and countries in your order data.
"""
)

# Footer
st.markdown("---")
st.markdown("Created with Streamlit by Tiago Gomes/Sweetcare")
