import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import country_converter as coco
import numpy as np
from pathlib import Path
import os
import sys

# Check if we're in the apps directory and adjust paths accordingly
parent_parts = Path(__file__).parent.parts
if parent_parts and parent_parts[-1] == "global-wacc":
    os.chdir(Path(__file__).parent.parent)
    sys.path.append(str(Path(__file__).parent.parent))

from scripts.country_waccs import (
    download_country_risk_premium,
    download_beta_data, 
    process_country_risk_premium,
    calculate_wacc_per_country,
    convert_wacc_nominal_to_real,
    calculate_wacc
)

# Configure the page

# Fraunhofer IEE color palette
IEE_COLORS = [
    "#005b7f", "#008598", "#179c7d", "#39c1cd", "#4CC2A6",
    "#669db2", "#a6bbc8", "#b2d235", "#C2D05C", "#face61",
    "#fce356", "#fdb913", "#f58220", "#d6a67c", "#f08591",
    "#a8508c", "#7c154d", "#bb0056", "#836bad", "#1c3f52",
    "#454545", "#C0C0C0", "#d3c7ae",
]

# Diverging color scale: IEE teal → neutral → IEE magenta (low WACC = good, high = risky)
IEE_DIVERGING = [
    [0.0, "#179c7d"],
    [0.15, "#4CC2A6"],
    [0.3, "#39c1cd"],
    [0.45, "#a6bbc8"],
    [0.55, "#d3c7ae"],
    [0.7, "#f08591"],
    [0.85, "#a8508c"],
    [1.0, "#7c154d"],
]

# Sequential color scale for single-direction metrics
IEE_SEQUENTIAL = [
    [0.0, "#005b7f"],
    [0.25, "#008598"],
    [0.5, "#39c1cd"],
    [0.75, "#a6bbc8"],
    [1.0, "#d3c7ae"],
]
st.set_page_config(
    page_title="Global WACC Calculator for Green PtX and Energy System Modelling",
    page_icon="🌐",
    layout="wide"
)

# Override Streamlit's default red accent with IEE muted blue-grey
st.markdown("""
<style>
    /* ── Global accent override ── */
    :root {
        --primary-color: #a6bbc8 !important;
    }

    /* ── Slider track (filled portion) ── */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: #005b7f !important;
    }
    .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] ~ div div {
        background-color: #a6bbc8 !important;
    }
    /* Slider thumb */
    .stSlider [data-baseweb="slider"] [role="slider"],
    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background: #005b7f !important;
        border-color: #005b7f !important;
    }
    /* Slider active track */
    .stSlider div[data-baseweb="slider"] > div:first-child > div {
        background: #a6bbc8 !important;
    }
    .stSlider div[data-baseweb="slider"] > div:first-child > div > div {
        background: #005b7f !important;
    }

    /* ── Radio buttons ── */
    .stRadio [role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        color: inherit;
    }
    .stRadio [role="radio"][aria-checked="true"] > div:first-child {
        background-color: #a6bbc8 !important;
        border-color: #a6bbc8 !important;
    }
    /* BaseWeb radio inner dot */
    div[data-baseweb="radio"] input:checked + div {
        background-color: #a6bbc8 !important;
        border-color: #a6bbc8 !important;
    }
    div[data-baseweb="radio"] input:checked + div div {
        background-color: #005b7f !important;
    }

    /* ── Checkboxes ── */
    .stCheckbox input:checked + div,
    .stCheckbox [data-testid="stCheckbox"] input:checked + div,
    div[data-baseweb="checkbox"] input:checked + div {
        background-color: #a6bbc8 !important;
        border-color: #a6bbc8 !important;
    }

    /* ── Select / multiselect ── */
    div[data-baseweb="select"] > div:focus-within {
        border-color: #a6bbc8 !important;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #a6bbc8 !important;
    }

    /* ── Buttons ── */
    button[kind="primary"],
    .stDownloadButton button {
        background-color: #a6bbc8 !important;
        border-color: #a6bbc8 !important;
        color: #1c3f52 !important;
    }
    button[kind="primary"]:hover,
    .stDownloadButton button:hover {
        background-color: #005b7f !important;
        border-color: #005b7f !important;
        color: white !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #a6bbc8 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #005b7f !important;
    }

    /* ── Spinners / progress ── */
    .stSpinner > div > div {
        border-top-color: #a6bbc8 !important;
    }

    /* ── Links ── */
    a { color: #005b7f !important; }
    a:hover { color: #008598 !important; }

    /* ── Text inputs focus ring ── */
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus {
        border-color: #a6bbc8 !important;
        box-shadow: 0 0 0 1px #a6bbc8 !important;
    }

    /* ── Toggle / switch ── */
    .stToggle input:checked + div {
        background-color: #a6bbc8 !important;
    }

    /* ── Info/success boxes keep their own styling ── */
</style>
""", unsafe_allow_html=True)

st.title("Global WACC Calculator for Green PtX and Energy System Modelling")

# Initialize the CountryConverter object
cc = coco.CountryConverter()

@st.cache_data
def load_and_calculate_wacc(skip_download=True):
    """Load country data and calculate base WACC with caching"""
    try:
        # Create output directory
        output_path = Path(__file__).resolve().parent / "data"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Load data with skip_download for faster performance
        crp_data_raw = download_country_risk_premium(output_path=output_path, skip_download=skip_download)
        beta_data = download_beta_data(output_path=output_path, skip_download=skip_download)
        country_data = process_country_risk_premium(output_path=output_path, crp_data_raw=crp_data_raw)

        # Add UN regions using country_converter
        if len(country_data) > 0:
            country_codes = country_data.index.tolist()
            regions = cc.convert(country_codes, to='UNregion')
            
            # Handle cases where conversion might fail
            region_mapping = {}
            for i, code in enumerate(country_codes):
                try:
                    region = regions[i] if isinstance(regions, list) else regions
                    region_mapping[code] = region if region != 'not found' else 'Other'
                except:
                    region_mapping[code] = 'Other'
            
            country_data['un_region'] = country_data.index.map(region_mapping)
            country_data['un_region'] = country_data['un_region'].fillna('Other')

        # Add Mauritania (MRT) using average values from reference countries
        ct_ref_list_for_mrt = ['EGY', 'KEN', 'NAM']
        if 'MRT' not in country_data.index:
            mrt_avg = country_data[country_data.index.isin(ct_ref_list_for_mrt)].mean(numeric_only=True)
            mrt_row = mrt_avg.to_dict()
            mrt_row['country_name'] = 'Mauritania'
            mrt_row['un_region'] = 'Sub-Saharan Africa'
            country_data.loc['MRT'] = mrt_row

        return country_data, True
        
    except Exception as e:
        st.error(f"Error loading WACC data: {e}")
        return pd.DataFrame(), False

@st.cache_data
def calculate_wacc_with_params(country_data, params):
    """Recalculate WACC based on user parameters"""
    if len(country_data) == 0:
        return pd.DataFrame()
    
    try:
        wacc_results = calculate_wacc_per_country(
            country_data=country_data,
            r_free=params['r_free'],
            beta_unleveraged=params['beta'],
            erp=params['erp'],
            r_debt=params['r_debt'],
            equity_ratio=params['equity_ratio'],
            debt_ratio=params['debt_ratio'],
            use_country_erp=params['use_country_erp']
        )
        
        # Add real WACC
        wacc_results['wacc_real'] = wacc_results['wacc'].apply(
            lambda nominal_wacc: convert_wacc_nominal_to_real(nominal_wacc, params['inflation_rate'])
        )
        
        # Add cost of equity and cost of debt components
        wacc_results['cost_of_equity'] = (
            wacc_results['risk_free_rate'] + 
            wacc_results['beta'] * wacc_results['equity_risk_premium'] + 
            wacc_results['country_risk_premium']
        )
        wacc_results['cost_of_debt'] = wacc_results['debt_rate'] * (1 - wacc_results['tax_rate'])
        
        # Add UN regions
        if 'un_region' in country_data.columns:
            region_map = country_data['un_region'].to_dict()
            wacc_results['un_region'] = wacc_results['country_code'].map(region_map)

        # Add Mauritania (MRT) using average values from reference countries
        # Note: rough estimate, replace with actual data when available
        ct_ref_list_for_mrt = ['EGY', 'KEN', 'NAM']
        if 'MRT' not in wacc_results['country_code'].values:
            mrt_avg = wacc_results[wacc_results['country_code'].isin(ct_ref_list_for_mrt)].mean(numeric_only=True)
            mrt_row = mrt_avg.to_dict()
            mrt_row['country_code'] = 'MRT'
            mrt_row['country_name'] = 'Mauritania'
            if 'un_region' in wacc_results.columns:
                mrt_row['un_region'] = 'Sub-Saharan Africa'
            wacc_results = pd.concat([wacc_results, pd.DataFrame([mrt_row])], ignore_index=True)

        return wacc_results
        
    except Exception as e:
        st.error(f"Error calculating WACC: {e}")
        return pd.DataFrame()

def create_sensitivity_analysis(base_params, country_data, selected_countries):
    """Generate sensitivity analysis data for selected countries"""
    
    if len(selected_countries) == 0:
        return pd.DataFrame()
    
    # Parameters to vary and their ranges
    sensitivity_params = {
        'r_free': np.linspace(base_params['r_free'] * 0.5, base_params['r_free'] * 1.5, 11),
        'beta': np.linspace(base_params['beta'] * 0.7, base_params['beta'] * 1.3, 11),
        'erp': np.linspace(base_params['erp'] * 0.7, base_params['erp'] * 1.3, 11),
        'equity_ratio': np.linspace(0.2, 0.8, 11)
    }
    
    sensitivity_results = []
    
    for param_name, param_values in sensitivity_params.items():
        for param_value in param_values:
            # Create modified parameters
            modified_params = base_params.copy()
            modified_params[param_name] = param_value
            
            # Calculate debt ratio if equity ratio changed
            if param_name == 'equity_ratio':
                modified_params['debt_ratio'] = 1 - param_value
            
            # Calculate WACC for selected countries only
            for country_code in selected_countries:
                if country_code in country_data.index:
                    country_row = country_data.loc[country_code]
                    
                    country_crp = country_row['country_risk_premium']
                    country_tax = country_row['tax_rate'] * 0.5
                    
                    # Use country-specific ERP if option is enabled
                    if modified_params['use_country_erp'] and pd.notna(country_row['equity_risk_premium']):
                        country_erp = country_row['equity_risk_premium']
                    else:
                        country_erp = modified_params['erp']
                    
                    # Calculate relevered beta using Hamada's equation
                    beta_relevered = modified_params['beta'] * (1 + ((1 - country_tax) * modified_params['debt_ratio'] / modified_params['equity_ratio']))
                    
                    wacc_value = calculate_wacc(
                        modified_params['r_free'],
                        beta_relevered,
                        country_erp,
                        country_crp,
                        modified_params['r_debt'],
                        country_tax,
                        modified_params['equity_ratio'],
                        modified_params['debt_ratio']
                    )
                    
                    # Calculate real WACC
                    wacc_real_value = convert_wacc_nominal_to_real(wacc_value, modified_params['inflation_rate'])
                    
                    sensitivity_results.append({
                        'parameter': param_name,
                        'parameter_value': param_value,
                        'country_code': country_code,
                        'country_name': country_row['country_name'],
                        'wacc': wacc_value,
                        'wacc_real': wacc_real_value
                    })
    
    return pd.DataFrame(sensitivity_results)

# Load data
with st.spinner("Loading WACC data..."):
    country_data, data_loaded = load_and_calculate_wacc(skip_download=True)

if not data_loaded or len(country_data) == 0:
    st.error("Could not load WACC data. Please ensure the data files are available.")
    st.stop()

# Sidebar - Interactive Parameters
with st.sidebar:
    st.header("Model Parameters")
    
    # Financial parameters
    st.subheader("Financial Parameters")
    r_free = st.slider("Risk-Free Rate (%)", 1.0, 6.0, 3.5, 0.1, help="Government bond yield") / 100
    beta = st.slider("Beta Factor (Unleveraged)", 0.5, 2.0, 1.1, 0.01, help="Unleveraged industry beta - will be relevered for each country based on tax and debt/equity ratio")
    erp = st.slider("Equity Risk Premium (%)", 3.0, 12.0, 6.5, 0.1, help="Market return premium over risk-free rate") / 100
    
    # New option for country-specific ERP
    use_country_erp = st.checkbox(
        "Use Country-Specific ERP", 
        value=False, 
        help="Use country-specific equity risk premium when available, otherwise fall back to global ERP"
    )
    
    debt_spread = st.slider("Debt Spread (%)", 1.0, 8.0, 2.0, 0.1, help="Credit margin over SWAP rate for debt") / 100
    swap_rate = st.slider("SWAP Rate (%)", 1.0, 6.0, 3.0, 0.1, help="Interest rate swap benchmark") / 100
    r_debt = swap_rate + debt_spread
    
    st.subheader("Capital Structure")
    equity_ratio = st.slider("Equity Ratio (%)", 20, 80, 40, 1, help="Share of equity financing") / 100
    debt_ratio = 1 - equity_ratio
    
    st.subheader("Economic Parameters")
    inflation_rate = st.slider("Inflation Rate (%)", 0.0, 5.0, 2.0, 0.1, help="Expected annual inflation") / 100
    
    st.markdown("---")
    st.header("View Controls")

    st.subheader("Country Filter")
    # Get available regions and countries
    available_regions = sorted(country_data['un_region'].unique().tolist()) if 'un_region' in country_data.columns else []
    available_countries = sorted(country_data.index.tolist())
    
    selected_regions = st.multiselect(
        "Filter by Regions",
        options=available_regions,
        default=[],
        help="Select regions to focus analysis"
    )
    
    # Filter countries based on selected regions
    if selected_regions:
        filtered_countries = country_data[country_data['un_region'].isin(selected_regions)].index.tolist()
    else:
        filtered_countries = available_countries
    
    # Default countries for comparison (key PtX markets)
    default_comparison_countries = ['CHL','ZAF','EGY','MAR','DEU']
    # Only include defaults that are available in the filtered countries
    available_defaults = [c for c in default_comparison_countries if c in filtered_countries]
    # If no defaults available, fall back to first 5 filtered countries
    if not available_defaults:
        available_defaults = filtered_countries[:5] if len(filtered_countries) >= 5 else filtered_countries
    
    selected_countries = st.multiselect(
        "Select Countries for Comparison",
        options=filtered_countries,
        default=available_defaults,
        help="Countries to include in detailed analysis (default: key PtX markets)"
    )
    
    st.subheader("Display")
    top_n = st.slider("Top N Countries to Display", 5, min(50, len(country_data)), 15)
    lowest_n = st.slider("Show Lowest N WACC Countries", 5, min(30, len(country_data)), 10, help="Number of countries with lowest WACC to display")
    st.caption("Hide sections to simplify the view")
    show_regional_charts = st.checkbox("WACC components & regional charts", value=True, help="WACC component breakdown and regional charts in Country Rankings and Geographic tabs")
    show_lowest_section = st.checkbox("Lowest WACC countries", value=True, help="Lowest WACC countries view in Country Rankings tab")
    show_sensitivity = st.checkbox("Sensitivity analysis", value=True, help="Full sensitivity analysis with tornado chart and heatmap")
    show_advanced = st.checkbox("Advanced analysis", value=True, help="Statistical analysis in Geographic tab; scenario analysis in Sensitivity tab")

# Prepare parameters dictionary
params = {
    'r_free': r_free,
    'beta': beta,
    'erp': erp,
    'swap_rate': swap_rate,
    'debt_spread': debt_spread,
    'r_debt': r_debt,
    'equity_ratio': equity_ratio,
    'debt_ratio': debt_ratio,
    'inflation_rate': inflation_rate,
    'use_country_erp': use_country_erp
}

# Calculate WACC with current parameters
with st.spinner("Calculating WACC..."):
    wacc_results = calculate_wacc_with_params(country_data, params)

if len(wacc_results) == 0:
    st.error("Could not calculate WACC results.")
    st.stop()

# Apply region filter to results
if selected_regions and 'un_region' in wacc_results.columns:
    wacc_results = wacc_results[wacc_results['un_region'].isin(selected_regions)]

# Key Metrics Dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_wacc_real = wacc_results['wacc_real'].mean()
    st.metric("Average Real WACC", f"{avg_wacc_real:.2%}")

with col2:
    min_wacc_real = wacc_results['wacc_real'].min()
    st.metric("Lowest Real WACC", f"{min_wacc_real:.2%}")

with col3:
    countries_analyzed = len(wacc_results)
    st.metric("Countries Analyzed", f"{countries_analyzed}")

with col4:
    wacc_range_real = f"{wacc_results['wacc_real'].min():.2%} - {wacc_results['wacc_real'].max():.2%}"
    st.metric("Real WACC Range", wacc_range_real)

# Create tabs for different visualizations
tab1, tab2, tab3, tab4 = st.tabs([
    "Country Rankings",
    "Geographic View",
    "Sensitivity Analysis",
    "Info",
])

with tab1:
    st.header("Country Rankings")

    view_mode = st.radio(
        "View",
        ["Selected Countries", "Top N Highest WACC", "Top N Lowest WACC"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if view_mode == "Selected Countries":
        if len(selected_countries) > 0:
            selected_data = wacc_results[wacc_results['country_code'].isin(selected_countries)]
            selected_data = selected_data.sort_values('wacc_real', ascending=False)

            st.caption(f"{len(selected_data)} countries selected · avg real WACC {selected_data['wacc_real'].mean():.2%} · range {selected_data['wacc_real'].min():.2%}–{selected_data['wacc_real'].max():.2%}")

            fig_real_wacc = px.bar(
                selected_data,
                x='wacc_real',
                y='country_name',
                title='Real WACC by Selected Countries',
                labels={'wacc_real': 'Real WACC (%)', 'country_name': 'Country'},
                color='wacc_real',
                color_continuous_scale=IEE_DIVERGING,
                orientation='h'
            )
            fig_real_wacc.update_layout(showlegend=False, margin=dict(t=50))
            fig_real_wacc.update_traces(texttemplate='%{x:.2%}', textposition='outside')
            st.plotly_chart(fig_real_wacc, use_container_width=True)

            if show_regional_charts:
                col1, col2 = st.columns(2)
                with col1:
                    fig_components = go.Figure()
                    fig_components.add_trace(go.Bar(
                        name='Cost of Equity (weighted)',
                        x=selected_data['country_name'],
                        y=selected_data['cost_of_equity'] * selected_data['equity_ratio'],
                        marker_color='#005b7f'
                    ))
                    fig_components.add_trace(go.Bar(
                        name='Cost of Debt (weighted)',
                        x=selected_data['country_name'],
                        y=selected_data['cost_of_debt'] * selected_data['debt_ratio'],
                        marker_color='#f58220'
                    ))
                    fig_components.update_layout(
                        title='WACC Components by Country',
                        barmode='stack',
                        xaxis_title='Country',
                        yaxis_title='Weighted Cost (%)',
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig_components, use_container_width=True)
                with col2:
                    first_country = selected_data.iloc[0]
                    components_data = {
                        'Component': ['Risk-Free Rate', 'Beta × ERP', 'Country Risk Premium', 'Tax Shield'],
                        'Value (%)': [
                            first_country['risk_free_rate'],
                            first_country['beta'] * first_country['equity_risk_premium'],
                            first_country['country_risk_premium'],
                            -first_country['debt_rate'] * first_country['tax_rate'] * first_country['debt_ratio']
                        ]
                    }
                    fig_breakdown = px.bar(
                        components_data,
                        x='Component',
                        y='Value (%)',
                        title=f'WACC Breakdown: {first_country["country_name"]}',
                        color='Value (%)',
                        color_continuous_scale=IEE_DIVERGING
                    )
                    fig_breakdown.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_breakdown, use_container_width=True)
        else:
            st.info("Please select countries in the sidebar.")

    elif view_mode == "Top N Highest WACC":
        top_countries_real = wacc_results.nlargest(top_n, 'wacc_real')
        top_countries_real = top_countries_real.sort_values('wacc_real', ascending=False)

        st.caption(f"Top {top_n} countries by highest real WACC · avg {top_countries_real['wacc_real'].mean():.2%} · range {top_countries_real['wacc_real'].min():.2%}–{top_countries_real['wacc_real'].max():.2%}")

        col1, col2 = st.columns([2, 1])
        with col1:
            fig_wacc_real = px.bar(
                top_countries_real,
                x='wacc_real',
                y='country_name',
                color='wacc_real',
                color_continuous_scale=IEE_DIVERGING,
                title=f'Real WACC by Country (Top {top_n})',
                labels={'wacc_real': 'Real WACC (%)', 'country_name': 'Country'},
                height=500,
                orientation='h'
            )
            fig_wacc_real.update_layout(showlegend=False, margin=dict(t=50))
            fig_wacc_real.update_traces(texttemplate='%{x:.2%}', textposition='outside')
            st.plotly_chart(fig_wacc_real, use_container_width=True)
        with col2:
            fig_hist_real = px.histogram(
                wacc_results,
                x='wacc_real',
                nbins=20,
                title='Real WACC Distribution',
                labels={'wacc_real': 'Real WACC (%)', 'count': 'Number of Countries'}
            )
            fig_hist_real.update_layout(showlegend=False)
            st.plotly_chart(fig_hist_real, use_container_width=True)

        st.subheader("Detailed Country Comparison")
        display_cols = ['country_name', 'wacc_real', 'country_risk_premium', 'tax_rate', 'cost_of_equity', 'cost_of_debt']
        if 'un_region' in wacc_results.columns:
            display_cols.insert(1, 'un_region')
        display_data = top_countries_real[display_cols].copy()
        pct_cols = ['wacc_real', 'country_risk_premium', 'tax_rate', 'cost_of_equity', 'cost_of_debt']
        for col in pct_cols:
            if col in display_data.columns:
                display_data[col] = display_data[col].apply(lambda x: f"{x:.3%}")
        st.dataframe(display_data, use_container_width=True)

    else:  # Top N Lowest WACC
        if show_lowest_section:
            lowest_countries_real = wacc_results.nsmallest(lowest_n, 'wacc_real')
            lowest_countries_real = lowest_countries_real.sort_values('wacc_real', ascending=False)

            st.caption(f"Top {lowest_n} countries by lowest real WACC · avg {lowest_countries_real['wacc_real'].mean():.2%} · range {lowest_countries_real['wacc_real'].min():.2%}–{lowest_countries_real['wacc_real'].max():.2%}")

            col1, col2 = st.columns([2, 1])
            with col1:
                fig_lowest_real = px.bar(
                    lowest_countries_real,
                    x='wacc_real',
                    y='country_name',
                    color='wacc_real',
                    color_continuous_scale=IEE_DIVERGING,
                    title=f'Countries with Lowest Real WACC (Top {lowest_n})',
                    labels={'wacc_real': 'Real WACC (%)', 'country_name': 'Country'},
                    height=500,
                    orientation='h'
                )
                fig_lowest_real.update_layout(showlegend=False, margin=dict(t=50))
                fig_lowest_real.update_traces(texttemplate='%{x:.2%}', textposition='outside')
                st.plotly_chart(fig_lowest_real, use_container_width=True)
            with col2:
                st.metric("Average Real WACC (Lowest)", f"{lowest_countries_real['wacc_real'].mean():.2%}")
                st.metric("Lowest Real WACC Country", lowest_countries_real.iloc[0]['country_name'])
                st.metric("Lowest Real WACC Value", f"{lowest_countries_real.iloc[0]['wacc_real']:.2%}")
                if 'un_region' in lowest_countries_real.columns:
                    region_counts = lowest_countries_real['un_region'].value_counts()
                    st.write("**Regional Distribution:**")
                    for region, count in region_counts.items():
                        st.write(f"• {region}: {count} countries")

            st.subheader("Detailed Analysis — Lowest Real WACC Countries")
            display_cols = ['country_name', 'wacc_real', 'country_risk_premium', 'tax_rate', 'cost_of_equity', 'cost_of_debt']
            if 'un_region' in lowest_countries_real.columns:
                display_cols.insert(1, 'un_region')
            display_data_lowest = lowest_countries_real[display_cols].copy()
            pct_cols = ['wacc_real', 'country_risk_premium', 'tax_rate', 'cost_of_equity', 'cost_of_debt']
            for col in pct_cols:
                if col in display_data_lowest.columns:
                    display_data_lowest[col] = display_data_lowest[col].apply(lambda x: f"{x:.3%}")
            st.dataframe(display_data_lowest, use_container_width=True)
        else:
            st.info("Lowest WACC countries section is hidden. Enable **Lowest WACC countries** in Display Options in the sidebar.")


with tab2:
    st.header("Geographic Real WACC Distribution")
    
    try:
        # Create world map with Real WACC data
        # Add ISO3 codes for mapping
        wacc_results['iso_alpha'] = wacc_results['country_code']
        
        fig_map_real = px.choropleth(
            wacc_results,
            locations='iso_alpha',
            color='wacc_real',
            hover_name='country_name',
            hover_data={'wacc_real': ':.3%', 'country_risk_premium': ':.3%'},
            color_continuous_scale=IEE_DIVERGING,
            title='Real WACC by Country - World Map',
            labels={'wacc_real': 'Real WACC (%)'}
        )
        
        fig_map_real.update_geos(
            domain=dict(x=[0, 0.88], y=[0, 1])
        )
        fig_map_real.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            coloraxis_colorbar=dict(
                x=0.89,
                xanchor='left',
                len=0.6,
                thickness=12,
            )
        )
        st.plotly_chart(fig_map_real, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating map visualization: {e}")
        st.info("Geographic visualization requires proper country codes.")
    
    # Regional Real WACC Analysis
    if show_regional_charts:
        st.subheader("Regional Real WACC Analysis")
    
    if show_regional_charts and 'un_region' in wacc_results.columns:
        # Regional comparison with real WACC
        regional_wacc = wacc_results.groupby('un_region').agg({
            'wacc_real': ['mean', 'std'],
            'country_risk_premium': 'mean',
            'tax_rate': 'mean'
        }).round(4)
        
        regional_wacc.columns = ['WACC_Real_Mean', 'WACC_Real_Std', 'CRP_Mean', 'Tax_Mean']
        regional_wacc = regional_wacc.reset_index()
        
        # Regional real WACC comparison
        fig_regional_real = px.bar(
            regional_wacc,
            x='un_region',
            y='WACC_Real_Mean',
            error_y='WACC_Real_Std',
            title='Average Real WACC by Region',
            labels={'WACC_Real_Mean': 'Average Real WACC (%)', 'un_region': 'Region'},
            color='WACC_Real_Mean',
            color_continuous_scale=IEE_DIVERGING
        )
        fig_regional_real.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_regional_real, use_container_width=True)
    
    # Regional bubble chart
    if show_regional_charts and 'un_region' in wacc_results.columns:
        fig_bubble = px.scatter(
            wacc_results,
            x='country_risk_premium',
            y='wacc_real',
            size='tax_rate',
            color='un_region',
            hover_name='country_name',
            color_discrete_sequence=IEE_COLORS,
            title='Real WACC vs Country Risk Premium',
            labels={
                'country_risk_premium': 'Country Risk Premium (%)',
                'wacc_real': 'Real WACC (%)',
                'tax_rate': 'Tax Rate (%)'
            }
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    if show_advanced:
        with st.expander("Statistical Analysis", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Parameter Correlations")
                corr_data = wacc_results[['wacc_real', 'country_risk_premium', 'tax_rate', 'cost_of_equity', 'cost_of_debt']].corr()
                fig_corr = px.imshow(
                    corr_data,
                    title='Real WACC Components Correlation Matrix',
                    color_continuous_scale=IEE_DIVERGING
                )
                st.plotly_chart(fig_corr, use_container_width=True)
            with col2:
                st.subheader("Risk-Return Analysis")
                fig_scatter_real = px.scatter(
                    wacc_results,
                    x='country_risk_premium',
                    y='wacc_real',
                    color='un_region' if 'un_region' in wacc_results.columns else None,
                    hover_name='country_name',
                    color_discrete_sequence=IEE_COLORS,
                    title='Real WACC vs Country Risk',
                    labels={
                        'country_risk_premium': 'Country Risk Premium (%)',
                        'wacc_real': 'Real WACC (%)'
                    }
                )
                st.plotly_chart(fig_scatter_real, use_container_width=True)

with tab3:
    st.header("Real WACC Sensitivity Analysis")
    
    if not show_sensitivity:
        st.info("Sensitivity analysis is hidden. Enable **Sensitivity analysis** in Display Options in the sidebar.")
    elif len(selected_countries) > 0:
        with st.spinner("Calculating sensitivity analysis..."):
            sensitivity_data = create_sensitivity_analysis(params, country_data, selected_countries)
        
        if len(sensitivity_data) > 0:
            
            # User controls for sensitivity analysis
            col1, col2 = st.columns([1, 1])
            with col1:
                selected_country_for_detail = st.selectbox(
                    "Select Country for Detailed Analysis",
                    options=selected_countries,
                    index=0,
                    format_func=lambda x: country_data.loc[x, 'country_name']
                )
            with col2:
                show_all_countries = st.checkbox("Show All Countries on Charts", value=False)
            
            # Real WACC Sensitivity Analysis
            st.subheader("Real WACC Parameter Sensitivity")
            
            # Filter data if needed
            chart_data = sensitivity_data if show_all_countries else sensitivity_data[sensitivity_data['country_code'] == selected_country_for_detail]
            
            fig_sensitivity_real = px.line(
                chart_data,
                x='parameter_value',
                y='wacc_real',
                color='country_name',
                facet_col='parameter',
                facet_col_wrap=2,
                color_discrete_sequence=IEE_COLORS,
                title='Real WACC Sensitivity to Parameter Changes',
                labels={'wacc_real': 'Real WACC (%)', 'parameter_value': 'Parameter Value'},
                height=600
            )
            
            # Improve formatting
            fig_sensitivity_real.update_traces(line=dict(width=3))
            fig_sensitivity_real.update_layout(
                margin=dict(t=80),
                showlegend=True
            )
            
            # Unmatch x-axes so each parameter has its own scale
            fig_sensitivity_real.update_xaxes(matches=None, showticklabels=True)
            
            # Update facet titles for better readability
            fig_sensitivity_real.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1].replace("r_free", "Risk-Free Rate")
                                                                                      .replace("beta", "Beta Factor")
                                                                                      .replace("erp", "Equity Risk Premium")
                                                                                      .replace("equity_ratio", "Equity Ratio")))
            st.plotly_chart(fig_sensitivity_real, use_container_width=True)
            
            # Two-column layout for detailed analysis
            col1, col2 = st.columns(2)
            
            with col1:
                # Enhanced Tornado chart
                st.subheader(f"Sensitivity Ranking: {country_data.loc[selected_country_for_detail, 'country_name']}")
                
                country_sensitivity = sensitivity_data[sensitivity_data['country_code'] == selected_country_for_detail]
                
                # Calculate parameter impact ranges with base case reference for real WACC
                base_wacc_real = wacc_results[wacc_results['country_code'] == selected_country_for_detail]['wacc_real'].iloc[0]
                
                param_impacts = []
                param_labels = {
                    'r_free': 'Risk-Free Rate',
                    'beta': 'Beta Factor', 
                    'erp': 'Equity Risk Premium',
                    'equity_ratio': 'Equity Ratio'
                }
                
                for param in ['r_free', 'beta', 'erp', 'equity_ratio']:
                    param_data = country_sensitivity[country_sensitivity['parameter'] == param]
                    if len(param_data) > 0:
                        min_wacc_real = param_data['wacc_real'].min()
                        max_wacc_real = param_data['wacc_real'].max()
                        wacc_range = max_wacc_real - min_wacc_real
                        relative_impact = (wacc_range / base_wacc_real) * 100  # Percentage impact
                        
                        param_impacts.append({
                            'parameter': param_labels[param],
                            'impact_range': wacc_range,
                            'relative_impact': relative_impact,
                            'min_wacc': min_wacc_real,
                            'max_wacc': max_wacc_real
                        })
                
                if param_impacts:
                    impact_df = pd.DataFrame(param_impacts).sort_values('impact_range', ascending=True)
                    
                    fig_tornado = px.bar(
                        impact_df,
                        x='impact_range',
                        y='parameter',
                        orientation='h',
                        title=f'Parameter Impact on Real WACC',
                        labels={'impact_range': 'Real WACC Range (%)', 'parameter': 'Parameter'},
                        color='relative_impact',
                        color_continuous_scale=IEE_SEQUENTIAL,
                        height=400
                    )
                    fig_tornado.update_layout(
                        margin=dict(t=50),
                        coloraxis_colorbar=dict(title="Relative Impact (%)")
                    )
                    st.plotly_chart(fig_tornado, use_container_width=True)
                    
                    # Summary table
                    st.subheader("Impact Summary")
                    summary_df = impact_df[['parameter', 'impact_range', 'relative_impact']].copy()
                    summary_df['impact_range'] = summary_df['impact_range'].apply(lambda x: f"{x:.3%}")
                    summary_df['relative_impact'] = summary_df['relative_impact'].apply(lambda x: f"{x:.1f}%")
                    summary_df.columns = ['Parameter', 'Real WACC Range', 'Relative Impact']
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            with col2:
                # Parameter value vs WACC scatter for selected country
                st.subheader("Detailed Parameter Analysis")
                
                # Allow user to select which parameter to analyze in detail
                selected_param = st.selectbox(
                    "Parameter for Detailed View",
                    options=['r_free', 'beta', 'erp', 'equity_ratio'],
                    format_func=lambda x: param_labels[x],
                    index=0
                )
                
                detailed_data = country_sensitivity[country_sensitivity['parameter'] == selected_param]
                
                if len(detailed_data) > 0:
                    fig_detailed = px.scatter(
                        detailed_data,
                        x='parameter_value',
                        y='wacc_real',
                        title=f'{param_labels[selected_param]} vs Real WACC',
                        labels={
                            'parameter_value': f'{param_labels[selected_param]} Value',
                            'wacc_real': 'Real WACC (%)'
                        },
                        color_discrete_sequence=['#005b7f'],
                        height=300
                    )
                    
                    # Add trend line
                    fig_detailed.add_traces(
                        px.line(detailed_data, x='parameter_value', y='wacc_real').data
                    )
                    
                    # Add base case marker
                    base_param_value = params[selected_param]
                    fig_detailed.add_trace(
                        go.Scatter(
                            x=[base_param_value],
                            y=[base_wacc_real],
                            mode='markers',
                            marker=dict(size=12, color='#7c154d', symbol='diamond'),
                            name='Base Case'
                        )
                    )
                    
                    fig_detailed.update_layout(margin=dict(t=50))
                    st.plotly_chart(fig_detailed, use_container_width=True)
                    
                    # Show parameter statistics
                    param_min = detailed_data['parameter_value'].min()
                    param_max = detailed_data['parameter_value'].max()
                    wacc_at_min = detailed_data[detailed_data['parameter_value'] == param_min]['wacc_real'].iloc[0]
                    wacc_at_max = detailed_data[detailed_data['parameter_value'] == param_max]['wacc_real'].iloc[0]
                    
                    st.metric("Base Case Real WACC", f"{base_wacc_real:.3%}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Min Scenario", f"{wacc_at_min:.3%}", f"{wacc_at_min - base_wacc_real:.3%}")
                    with col_b:
                        st.metric("Max Scenario", f"{wacc_at_max:.3%}", f"{wacc_at_max - base_wacc_real:.3%}")
            
            # Cross-parameter heatmap for advanced analysis
            st.subheader("Cross-Parameter Analysis")
            st.caption("Shows how WACC changes when two parameters vary simultaneously")
            
            # Create heatmap data for two most impactful parameters
            if len(param_impacts) >= 2:
                # Get top 2 most impactful parameters
                top_params = sorted(param_impacts, key=lambda x: x['impact_range'], reverse=True)[:2]
                param1_name = [k for k, v in param_labels.items() if v == top_params[0]['parameter']][0]
                param2_name = [k for k, v in param_labels.items() if v == top_params[1]['parameter']][0]
                
                # Create grid for heatmap
                param1_values = np.linspace(params[param1_name] * 0.7, params[param1_name] * 1.3, 10)
                param2_values = np.linspace(params[param2_name] * 0.7, params[param2_name] * 1.3, 10)
                
                heatmap_data = []
                for p1_val in param1_values:
                    for p2_val in param2_values:
                        # Calculate WACC with both parameters changed
                        country_row = country_data.loc[selected_country_for_detail]
                        country_crp = country_row['country_risk_premium']
                        country_tax = country_row['tax_rate'] * 0.5
                        
                        modified_params = params.copy()
                        modified_params[param1_name] = p1_val
                        modified_params[param2_name] = p2_val
                        
                        if param1_name == 'equity_ratio':
                            modified_params['debt_ratio'] = 1 - p1_val
                        if param2_name == 'equity_ratio':
                            modified_params['debt_ratio'] = 1 - p2_val
                        
                        # Calculate relevered beta using Hamada's equation
                        beta_relevered = modified_params['beta'] * (1 + ((1 - country_tax) * modified_params['debt_ratio'] / modified_params['equity_ratio']))
                        
                        wacc_val = calculate_wacc(
                            modified_params['r_free'],
                            beta_relevered,
                            modified_params['erp'],
                            country_crp,
                            modified_params['r_debt'],
                            country_tax,
                            modified_params['equity_ratio'],
                            modified_params['debt_ratio']
                        )
                        
                        heatmap_data.append({
                            param1_name: p1_val,
                            param2_name: p2_val,
                            'wacc': wacc_val
                        })
                
                heatmap_df = pd.DataFrame(heatmap_data)
                heatmap_pivot = heatmap_df.pivot(index=param2_name, columns=param1_name, values='wacc')
                
                fig_heatmap = px.imshow(
                    heatmap_pivot,
                    title=f'WACC Heatmap: {param_labels[param1_name]} vs {param_labels[param2_name]}',
                    labels={
                        'x': param_labels[param1_name],
                        'y': param_labels[param2_name],
                        'color': 'WACC (%)'
                    },
                    color_continuous_scale=IEE_DIVERGING,
                    height=400
                )
                fig_heatmap.update_layout(margin=dict(t=50))
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                st.info(f"""
                **Key Insights**: 
                - **Most sensitive parameter**: {top_params[0]['parameter']} (±{top_params[0]['relative_impact']:.1f}% impact)
                - **Second most sensitive**: {top_params[1]['parameter']} (±{top_params[1]['relative_impact']:.1f}% impact)
                - **Base case Real WACC**: {base_wacc_real:.3%}
                - **Total Real WACC range**: {wacc_results['wacc_real'].min():.3%} - {wacc_results['wacc_real'].max():.3%} across all countries
                """)
        else:
            st.warning("Could not generate sensitivity analysis data.")
    elif show_sensitivity:
        st.info("Please select countries in the sidebar to perform sensitivity analysis.")

    if show_advanced:
        with st.expander("Scenario Analysis", expanded=False):
            scenarios = {
                'Conservative': {'r_free': r_free * 0.7, 'erp': erp * 0.8, 'beta': beta * 0.9},
                'Base Case': {'r_free': r_free, 'erp': erp, 'beta': beta},
                'Aggressive': {'r_free': r_free * 1.3, 'erp': erp * 1.2, 'beta': beta * 1.1}
            }

            scenario_results = []
            for scenario_name, scenario_params in scenarios.items():
                scenario_wacc_params = params.copy()
                scenario_wacc_params.update(scenario_params)

                scenario_wacc = calculate_wacc_with_params(country_data, scenario_wacc_params)
                if len(scenario_wacc) > 0:
                    avg_wacc_real = scenario_wacc['wacc_real'].mean()
                    scenario_results.append({
                        'Scenario': scenario_name,
                        'Average Real WACC': f"{avg_wacc_real:.3%}",
                        'Min Real WACC': f"{scenario_wacc['wacc_real'].min():.3%}",
                        'Max Real WACC': f"{scenario_wacc['wacc_real'].max():.3%}"
                    })

            if scenario_results:
                scenario_df = pd.DataFrame(scenario_results)
                st.dataframe(scenario_df, use_container_width=True)

                scenario_plot_data = []
                for result in scenario_results:
                    scenario_plot_data.append({
                        'Scenario': result['Scenario'],
                        'Average': float(result['Average Real WACC'].strip('%')) / 100,
                        'Min': float(result['Min Real WACC'].strip('%')) / 100,
                        'Max': float(result['Max Real WACC'].strip('%')) / 100
                    })

                scenario_plot_df = pd.DataFrame(scenario_plot_data)

                fig_scenario = px.bar(
                    scenario_plot_df,
                    x='Scenario',
                    y='Average',
                    title='Scenario Analysis: Average Real WACC Comparison',
                    labels={'Average': 'Average Real WACC (%)'},
                    color='Average',
                    color_continuous_scale=IEE_DIVERGING
                )

                st.plotly_chart(fig_scenario, use_container_width=True)

# Info tab — methodology, formulas, and sources
with tab4:
    st.header("Methodology")

    st.markdown("""
    This tool calculates the **Weighted Average Cost of Capital (WACC)** for each country,
    combining a country-specific cost of equity with a uniform cost of debt.
    All country-varying inputs (country risk premium, corporate tax rate) are sourced
    from Aswath Damodaran's publicly available datasets.
    """)

    st.subheader("WACC Formula")
    st.latex(r"""
    WACC_{nominal} = r_E \cdot w_E \;+\; r_D \,(1 - \tau) \cdot w_D
    """)

    st.markdown("""
    | Symbol | Description | Default |
    |--------|-------------|--------:|
    | $r_E$  | Cost of equity | (computed) |
    | $r_D$  | Pre-tax cost of debt (SWAP rate + credit margin) | 5.0 % |
    | $\\tau$ | Corporate tax rate (country-specific) | varies |
    | $w_E$  | Equity ratio | 40 % |
    | $w_D$  | Debt ratio ($1 - w_E$) | 60 % |
    """)

    st.subheader("Cost of Equity (CAPM)")
    st.latex(r"""
    r_E = r_f \;+\; \beta_L \cdot ERP \;+\; CRP
    """)

    st.markdown("""
    | Symbol | Description | Default |
    |--------|-------------|--------:|
    | $r_f$    | Risk-free rate (long-term government bond yield) | 3.5 % |
    | $\\beta_L$ | Levered beta (re-levered per country, see below) | (computed) |
    | $ERP$    | Equity risk premium (global or country-specific) | 6.5 % |
    | $CRP$    | Country risk premium (Damodaran) | varies |
    """)

    st.subheader("Beta Re-levering (Hamada's Equation)")
    st.latex(r"""
    \beta_L = \beta_U \cdot \left(1 + \frac{(1 - \tau)\, w_D}{w_E}\right)
    """)

    st.markdown("""
    | Symbol | Description | Default |
    |--------|-------------|--------:|
    | $\\beta_U$ | Unleveraged (asset) beta — Green & Renewable Energy sector | 1.13 |
    | $\\tau$    | Country-specific corporate tax rate | varies |
    """)

    st.subheader("Real WACC (Fisher Equation)")
    st.latex(r"""
    WACC_{real} = \frac{1 + WACC_{nominal}}{1 + \pi} - 1
    """)

    st.markdown("""
    | Symbol | Description | Default |
    |--------|-------------|--------:|
    | $\\pi$ | Expected annual inflation rate | 2.0 % |

    The real WACC is the relevant discount rate when investment costs and
    cash-flows are expressed in constant (inflation-adjusted) monetary units,
    as is common in energy system models.
    """)

    st.subheader("Sources")
    st.markdown("""
    **WACC methodology:**
    - Brealey, R.A., Myers, S.C. & Allen, F. (2020). *Principles of Corporate Finance* (13th ed.). McGraw-Hill Education.
    - Reul, J., Mpinga, L., Graul, H., et al. (2025). *Renewable Ammonia: Kenya's Business Case.* H2Global Foundation.
      [Link](https://h2-global.org/library/renewable-ammonia-kenyas-business-case/)

    **Country risk & cost of equity (CAPM) literature:**
    - Damodaran, A. (2023). *Country Risk: Determinants, Measures and Implications — The 2023 Edition.*
      [DOI](https://doi.org/10.2139/ssrn.4509578)
    - Damodaran, A. (2023). *Equity Risk Premiums (ERP): Determinants, Estimation and Implications — The 2023 Edition.*
      [DOI](https://doi.org/10.2139/ssrn.4398884)

    **Country-specific data download (CRP, tax rate, beta):**
    - Damodaran, A. (2026). *Country Default Spreads and Risk Premiums.*
      NYU Stern School of Business.
      [Link](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html)
    - Damodaran, A. (2026). *Betas by Sector (US).*
      NYU Stern School of Business.
      [Link](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html)
    """)

    st.subheader("License")
    st.markdown("""
    This tool and its results are licensed under
    [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
    """)

# Footer
st.markdown("---")


# Download option with metadata
def create_csv_with_metadata(wacc_data, params):
    """Create CSV with metadata header"""
    from datetime import datetime
    
    # Create metadata header
    metadata_lines = [
        "# WACC Calculator for Global PtX Projects - Results",
        "# Author: Lukas Jansen",
        "# Sources: Aswath Damodaran. Country Default Spreads and Risk Premiums. https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html",
        "# Sources: Aswath Damodaran. Betas by Sector (US). https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html",
        "# Sources: Aswath Damodaran (2023). Country Risk: Determinants, Measures and Implications. https://doi.org/10.2139/ssrn.4509578",
        "# Sources: Aswath Damodaran (2023). Equity Risk Premiums (ERP). https://doi.org/10.2139/ssrn.4398884",
        "# Sources: Brealey, Myers & Allen (2020). Principles of Corporate Finance (13th ed.). McGraw-Hill Education.",
        "# Sources: Reul et al. (2025). Renewable Ammonia: Kenya's Business Case. H2Global Foundation. https://h2-global.org/library/renewable-ammonia-kenyas-business-case/",
        "# License: CC BY 4.0",
        "# Contact: lukas.jansen@iee.fraunhofer.de",
        f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Risk-free rate: {params['r_free']:.3%}",
        f"# Beta factor (unleveraged): {params['beta']:.3f}",
        f"# Equity risk premium: {params['erp']:.3%}",
        f"# SWAP rate: {params['swap_rate']:.3%}",
        f"# Credit margin (debt spread): {params['debt_spread']:.3%}",
        f"# Cost of debt (r_debt): {params['r_debt']:.3%}",
        f"# Equity ratio: {params['equity_ratio']:.1%}",
        f"# Debt ratio: {params['debt_ratio']:.1%}",
        f"# Inflation rate: {params['inflation_rate']:.3%}",
        f"# Use country-specific ERP: {params['use_country_erp']}",
        f"# Countries analyzed: {len(wacc_data)}",
        f"# Average real WACC: {wacc_data['wacc_real'].mean():.3%}",
        f"# WACC range: {wacc_data['wacc_real'].min():.3%} - {wacc_data['wacc_real'].max():.3%}",
        "#",
        "# Column descriptions:",
        "# country_code: ISO 3-letter country code",
        "# country_name: Full country name",
        "# wacc: Nominal weighted average cost of capital",
        "# wacc_real: Real WACC (inflation-adjusted)",
        "# country_risk_premium: Country-specific risk premium",
        "# risk_free_rate: Risk-free rate used",
        "# equity_risk_premium: Equity risk premium used",
        "# beta: Beta factor used",
        "# debt_rate: Cost of debt",
        "# tax_rate: Corporate tax rate",
        "# equity_ratio: Equity financing ratio",
        "# debt_ratio: Debt financing ratio",
        "# cost_of_equity: Cost of equity capital",
        "# cost_of_debt: After-tax cost of debt",
        "#"
    ]
    
    # Convert to string
    metadata_header = '\n'.join(metadata_lines) + '\n'
    
    # Get CSV data
    csv_data = wacc_data.to_csv(index=False)
    
    # Combine metadata and data
    full_csv = metadata_header + csv_data
    
    return full_csv.encode('utf-8')

csv_with_metadata = create_csv_with_metadata(wacc_results, params)


# Legal footer links
col1, col2, col3 = st.columns([3, 3, 3])
with col1:
    st.caption("Global WACC Calculator for Green PtX and Energy System Modelling | Licensed under CC BY 4.0")
    st.download_button(
    "Download WACC Results (with metadata)",
    csv_with_metadata,
    "wacc_results_with_metadata.csv",
    "text/csv",
    key='download-wacc-csv'
    )
with col2:
    st.caption("Lukas Jansen, 2025, Fraunhofer IEE, https://github.com/ljansen-iee/global-wacc.")
    st.caption("Sources: "
    "Damodaran (2026), [Country Risk Premiums](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html) "
    "& [Betas by Sector](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html); "
    "Damodaran (2023), [Country Risk](https://doi.org/10.2139/ssrn.4509578) "
    "& [ERP](https://doi.org/10.2139/ssrn.4398884); "
    "Brealey, Myers & Allen (2020), Principles of Corporate Finance; "
    "Reul et al. (2025), [Renewable Ammonia: Kenya's Business Case](https://h2-global.org/library/renewable-ammonia-kenyas-business-case/)")
with col3:
    st.markdown("[Imprint](https://www.iee.fraunhofer.de/en/publishing-notes.html)")
    st.markdown("[Data Protection](https://www.iee.fraunhofer.de/en/data_protection.html)")