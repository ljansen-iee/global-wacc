# Calculation of Weighted Average Cost of Capital (WACC)

import pandas as pd
import country_converter as coco
from pathlib import Path

# Default values for missing country data
CRP = 0.0951  # Default country risk premium (9.51%)
TAX = 0.3     # Default corporate tax rate (30%)


def download_country_risk_premium(output_path, skip_download=False):
    """
    Download country risk premium data from Damodaran's website
    
    Parameters:
    output_path (Path): Path to save output files
    skip_download (bool): If True, skip download and use fallback data immediately
    """
    if skip_download:
        print("Skipping download, using fallback data...")
        fallback_path = output_path / "country_risk_premium_raw.csv"
        try:
            crp_data_raw = pd.read_csv(fallback_path)
            print(f"Using fallback data from {fallback_path}")
            return crp_data_raw
        except FileNotFoundError:
            print(f"Fallback file {fallback_path} not found. Proceeding with download...")
    
    try:
        url = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html"

        print(f"Downloading country risk premium data from \n (Source: {url})...")
        table = pd.read_html(url, header=0)[1] # Skip the first table which is not relevant
        
        if len(table) > 150 and "Country Risk  Premium" in table.columns:
            crp_data_raw = table  
            crp_data_raw.to_csv(output_path / "country_risk_premium_raw.csv", index=False)
            print(f"Saved country risk premium data with {len(table)} rows and columns: {list(crp_data_raw.columns)}")      
            return crp_data_raw
        else: 
            raise ValueError("Unexpected table format or data rows.")        
        
    except Exception as e:
        print(f"Error downloading country risk premium data: {e}")

        fallback_path = output_path / "country_risk_premium_raw.csv"
        crp_data_raw = pd.read_csv(fallback_path)
        print(f"Falling back to using {fallback_path}")

        return crp_data_raw

def create_country_converter_map(output_path, crp_data_raw):
    """
    Create and save a country converter map for consistent country code conversion
    
    Parameters:
    output_path (Path): Path to save output files
    crp_data_raw (pd.DataFrame): Raw country risk premium data
    
    Returns:
    dict: Country name to ISO3 code mapping
    """
    print("Creating country converter map...")
    
    # Get column name for country
    country_col = 'Country' if 'Country' in crp_data_raw.columns else crp_data_raw.columns[0]
    
    # Extract unique country names
    country_names = crp_data_raw[country_col].dropna().astype(str).str.strip().unique()
    country_names = [name for name in country_names if name.lower() not in ['nan', 'none', '']]
    
    # Create mapping
    country_map = {}
    conversion_issues = []
    
    for country_name in country_names:
        try:
            country_code = coco.convert(country_name, to='ISO3')
            if country_code == 'not found':
                conversion_issues.append(country_name)
                country_map[country_name] = None  # Mark for manual review
            else:
                country_map[country_name] = country_code
        except Exception as e:
            print(f"Error converting {country_name}: {e}")
            conversion_issues.append(country_name)
            country_map[country_name] = None
    
    # Create DataFrame and save
    map_df = pd.DataFrame([
        {'country_name': name, 'iso3_code': code, 'needs_review': code is None}
        for name, code in country_map.items()
    ])
    
    map_file = output_path / "country_converter_map.csv"
    map_df.to_csv(map_file, index=False)
    
    print(f"Saved country converter map to {map_file}")
    print(f"Successfully converted {len([c for c in country_map.values() if c is not None])} countries")
    
    if conversion_issues:
        print(f"Found {len(conversion_issues)} countries needing manual review:")
        for issue in conversion_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(conversion_issues) > 10:
            print(f"  ... and {len(conversion_issues) - 10} more")
        print("Please review and manually correct the country_converter_map.csv file")
    
    return country_map

def load_country_converter_map(output_path):
    """
    Load the saved country converter map
    
    Parameters:
    output_path (Path): Path where output files are saved
    
    Returns:
    dict: Country name to ISO3 code mapping
    """
    map_file = output_path / "country_converter_map.csv"
    
    if not map_file.exists():
        return None
    
    try:
        map_df = pd.read_csv(map_file)
        
        # Convert to dictionary, excluding entries that need review (None values)
        country_map = {}
        for _, row in map_df.iterrows():
            if pd.notna(row['iso3_code']) and row['iso3_code'] != '':
                country_map[row['country_name']] = row['iso3_code']
        
        print(f"Loaded country converter map with {len(country_map)} valid mappings")
        return country_map
        
    except Exception as e:
        print(f"Error loading country converter map: {e}")
        return None

def show_country_map_info(output_path):
    """
    Display information about the current country converter map
    
    Parameters:
    output_path (Path): Path where output files are saved
    """
    map_file = output_path / "country_converter_map.csv"
    
    if not map_file.exists():
        print("No country converter map found")
        return
    
    try:
        map_df = pd.read_csv(map_file)
        total_countries = len(map_df)
        valid_mappings = len(map_df[map_df['iso3_code'].notna() & (map_df['iso3_code'] != '')])
        needs_review = len(map_df[map_df['needs_review'] == True])
        
        print(f"\nCountry Converter Map Status:")
        print(f"  Total countries: {total_countries}")
        print(f"  Valid mappings: {valid_mappings}")
        print(f"  Needs review: {needs_review}")
        
        if needs_review > 0:
            print(f"\nCountries needing review:")
            review_countries = map_df[map_df['needs_review'] == True]['country_name'].tolist()
            for country in review_countries[:5]:  # Show first 5
                print(f"  - {country}")
            if len(review_countries) > 5:
                print(f"  ... and {len(review_countries) - 5} more")
        
    except Exception as e:
        print(f"Error reading country converter map: {e}")

def process_country_risk_premium(output_path, crp_data_raw):
    """
    Process and clean up country-specific risk premiums and tax rates from downloaded data
    Uses saved country converter map for consistent country code conversion
    
    Parameters:
    output_path (Path): Path where output files are saved
    crp_data_raw (pd.DataFrame): Raw country risk premium data
    """
    print("Processing country-specific data...")
    
    # Load or create country converter map
    country_map = load_country_converter_map(output_path)
    if country_map is None:
        print("No existing country converter map found, creating new one...")
        country_map = create_country_converter_map(output_path, crp_data_raw)
    else:
        print("Using existing country converter map")
    
    def parse_percentage(value, default=None):
        """Helper function to parse percentage values"""
        if pd.isna(value) or str(value).lower().strip() in ['nan', 'none', '']:
            return default
        try:
            return float(str(value).replace('%', '').strip()) / 100
        except (ValueError, TypeError):
            return default
    
    def parse_string(value):
        """Helper function to parse string values"""
        if pd.isna(value) or str(value).lower().strip() in ['nan', 'none', '']:
            return None
        return str(value).strip()
    
    crp_data = {}
    
    if crp_data_raw is not None and len(crp_data_raw) > 1:
        try:
            # Column mapping
            cols = {
                'country': 'Country' if 'Country' in crp_data_raw.columns else crp_data_raw.columns[0],
                'crp': 'Country Risk  Premium' if 'Country Risk  Premium' in crp_data_raw.columns else crp_data_raw.columns[3],
                'tax': 'Corporate Tax  Rate' if 'Corporate Tax  Rate' in crp_data_raw.columns else crp_data_raw.columns[4],
                'adj_spread': 'Adj. Default  Spread' if 'Adj. Default  Spread' in crp_data_raw.columns else None,
                'erp': 'Equity Risk  Premium' if 'Equity Risk  Premium' in crp_data_raw.columns else None,
                'rating': "Moody's rating" if "Moody's rating" in crp_data_raw.columns else None
            }
            
            for _, row in crp_data_raw.iterrows():
                country_name_raw = str(row[cols['country']]).strip()
                
                if not country_name_raw or country_name_raw.lower() in ['nan', 'none', '']:
                    continue
                
                try:
                    # Use the saved country converter map
                    country_code = country_map.get(country_name_raw)
                    
                    if country_code is None:
                        print(f"Country not in converter map (skipping): {country_name_raw}")
                        continue
                    
                    crp_data[country_code] = {
                        'country_risk_premium': parse_percentage(row[cols['crp']], CRP),
                        'tax_rate': parse_percentage(row[cols['tax']], TAX),
                        'country_name': country_name_raw,
                        'adj_default_spread': parse_percentage(row[cols['adj_spread']]) if cols['adj_spread'] else None,
                        'equity_risk_premium': parse_percentage(row[cols['erp']]) if cols['erp'] else None,
                        'moodys_rating': parse_string(row[cols['rating']]) if cols['rating'] else None
                    }
                    
                except (ValueError, TypeError) as e:
                    print(f"Error parsing data for {country_name_raw}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error processing downloaded data: {e}")
            print("No country data could be processed")
    else:
        print("No valid CRP data available")
    
    crp_data_df = pd.DataFrame.from_dict(crp_data, orient='index')
    crp_data_df.index.name = 'country_iso3'
    
    crp_data_df.to_csv(output_path / "crp_data.csv", index=True)
    print(f"Saved country parameters for {len(crp_data_df)} countries to {output_path / 'crp_data.csv'}")
    
    return crp_data_df


def download_beta_data(output_path, skip_download=False):
    """
    Download beta data from Damodaran's website. 
    Note: Beta factors could also be calculated based on comparing specific power-to-X or renewables index with S&P 500 or MSCI World Index.
    
    Parameters:
    output_path (Path): Path to save output files
    skip_download (bool): If True, skip download and use fallback data immediately
    """
    if skip_download:
        print("Skipping beta data download, using fallback data...")
        fallback_path = output_path / "industry_beta_raw.csv"
        try:
            beta_data = pd.read_csv(fallback_path)
            print(f"Using fallback beta data from {fallback_path}")
            return beta_data
        except FileNotFoundError:
            print(f"Fallback file {fallback_path} not found. Proceeding with download...")
    
    try:
        url = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html"
        print("Downloading beta data...")
        
        tables = pd.read_html(url)
        
        # Find the industry beta table - typically the largest table with industry names
        beta_data = None
        for i, table in enumerate(tables):
            if len(table) > 150:  # Industry table should have many rows and columns
                # Check if first column contains industry names
                first_col_sample = table.iloc[1:6, 0].astype(str).str.lower()
                if any(industry in ' '.join(first_col_sample) for industry in ['energy', 'renewable', 'oil', 'utility']):
                    beta_data = table
                    print(f"Found beta table (table {i}) with {len(table)} rows")
                    break
                    
        if beta_data is None:
            # Fallback to largest table
            beta_data = max(tables, key=len) if tables else None
            print(f"Using largest table as fallback for beta data" if beta_data is not None else "No beta tables found")
            
        if beta_data is not None:
            # Save the raw data
            beta_data.to_csv(output_path / "industry_beta_raw.csv", index=False)
            print(f"Saved beta data with columns: {list(beta_data.columns)}")
        
        return beta_data
        
    except Exception as e:
        print(f"Error downloading beta data: {e}")
        print("Falling back to using and resaving data_repo/wacc/crp_data.csv")


        return None



def calculate_wacc(r_free, beta, erp, crp, r_debt, tax, equity_ratio, debt_ratio):
    """
    Calculate WACC based on provided parameters.

    Parameters:
    r_free (float): Risk-free rate (e.g., 4.5% as 0.045)
    beta (float): Beta factor for specific industry (e.g., 1.058)
    erp (float): Equity-risk premium (e.g., 6.5% as 0.065)
    crp (float): Country-risk premium (e.g., 9.51% as 0.0951)
    r_debt (float): Interest rate for debt (e.g., 5% as 0.05)
    tax (float): Corporate tax rate (e.g., 30% as 0.3)
    equity_ratio (float): Share of equity capital (default 0.4)
    debt_ratio (float): Share of debt capital (default 0.6)

    Returns:
    float: Calculated WACC
    """
    cost_of_equity = r_free + beta * erp + crp
    cost_of_debt = r_debt * (1 - tax)
    wacc = cost_of_equity * equity_ratio + cost_of_debt * debt_ratio
    return wacc

def calculate_wacc_per_country(country_data, r_free, beta_unleveraged, erp, r_debt, equity_ratio, debt_ratio, use_country_erp=False):
    """
    Calculate WACC for each country using country-specific parameters
    
    Parameters:
    use_country_erp (bool): If True, use country-specific equity risk premium when available,
                           otherwise use the global ERP value
    """
    print("Calculating WACC per country...")
    if use_country_erp:
        print("Using country-specific equity risk premium when available")
    
    wacc_results = []
    
    for country_code in country_data.index:
        country_crp = country_data.loc[country_code, 'country_risk_premium']
        country_tax = country_data.loc[country_code, 'tax_rate'] #* 0.5
        country_name = country_data.loc[country_code, 'country_name']
        
        # Use country-specific ERP if option is enabled and data is available
        if use_country_erp and pd.notna(country_data.loc[country_code, 'equity_risk_premium']):
            country_erp = country_data.loc[country_code, 'equity_risk_premium']
        else:
            country_erp = erp
        
        beta = beta_unleveraged * (1+((1-country_tax)*debt_ratio/equity_ratio))  # Hamada's equation to relever beta

        wacc_value = calculate_wacc(r_free, beta, country_erp, country_crp, r_debt, country_tax, equity_ratio, debt_ratio)
        
        wacc_results.append({
            'country_code': country_code,
            'country_name': country_name,
            'wacc': wacc_value,
            'risk_free_rate': r_free,
            'beta': beta,
            'equity_risk_premium': country_erp,
            'country_risk_premium': country_crp,
            'debt_rate': r_debt,
            'tax_rate': country_tax,
            'equity_ratio': equity_ratio,
            'debt_ratio': debt_ratio
        })
        
        # print(f"{country_code} ({country_name}): WACC = {wacc_value:.4%} (ERP: {country_erp:.4%})")
    
    return pd.DataFrame(wacc_results)

def convert_wacc_nominal_to_real(nominal_wacc, inflation_rate):
    """
    Convert nominal WACC to real WACC
    
    Parameters:
    nominal_wacc (float): Nominal WACC rate
    inflation_rate (float): Expected inflation rate
    
    Returns:
    float: Real WACC rate
    """
    return (1 + nominal_wacc) / (1 + inflation_rate) - 1

def convert_wacc_real_to_nominal(real_wacc, inflation_rate):
    """
    Convert real WACC to nominal WACC
    
    Parameters:
    real_wacc (float): Real WACC rate
    inflation_rate (float): Expected inflation rate
    
    Returns:
    float: Nominal WACC rate
    """
    return (1 + real_wacc) * (1 + inflation_rate) - 1

if __name__ == "__main__":
    output_path = Path(__file__).resolve().parent.parent / "data"
    output_path.mkdir(parents=True, exist_ok=True)

    # Set to True to skip downloads and use fallback data
    SKIP_DOWNLOAD = True

    # Set to True to regenerate the country converter map (useful if source data changes)
    RECREATE_COUNTRY_MAP = False  # Set to True to force regeneration of country converter map
                                    # The map is saved as global-wacc/data/country_converter_map.csv
                                    # and can be manually edited to fix country name conversions

    crp_data_raw = download_country_risk_premium(output_path, skip_download=SKIP_DOWNLOAD)
    beta_data = download_beta_data(output_path, skip_download=SKIP_DOWNLOAD)

    # Optionally regenerate country converter map
    if RECREATE_COUNTRY_MAP:
        print("Re-create country converter map...")
        map_file = output_path / "country_converter_map.csv"
        if map_file.exists():
            map_file.unlink()  # Delete existing map
        country_map = create_country_converter_map(output_path, crp_data_raw)

    country_data = process_country_risk_premium(output_path, crp_data_raw)




    EQUITY_RATIO = 0.40  # Default equity ratio
    DEBT_RATIO = 1 - EQUITY_RATIO  # Default debt ratio
    R_FREE = 0.035 # Risk-free rate (2.5% - more realistic global average for 2024/2025 and long-term)

    # Major Economies (10-year government bonds):
    # US Treasury: ~4.2-4.5% (but this is historically high due to recent Fed policy)
    # German Bund: ~2.2-2.5%
    # UK Gilt: ~4.0-4.3%
    # Japanese JGB: ~0.8-1.0%
    # EU average: ~2.5-3.5%
    BETA_UNLEVERAGED = 1.06 # source https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html --> Industry_Name: Green & Renewable Energy
    ERP = 0.10 - R_FREE # based on nominal long-term average return of stock market

    # CRP = 0.0951 # source https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html

    # TAX = 0.3 # source https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html

    R_DEBT = 0.03 + 0.02 # SWAP rate,  2% credit margin

    # Inflation rate for real WACC calculation (adjust based on your model assumptions)
    INFLATION_RATE = 0.02  # 2% annual inflation assumption

    # Option to use country-specific equity risk premium instead of global ERP
    USE_COUNTRY_ERP = False  # Set to True to use country-specific equity risk premium when available
                            # Falls back to global ERP value if country-specific data is not available


    # Calculate nominal WACC per country
    wacc_per_country = calculate_wacc_per_country(
        country_data=country_data,
        r_free=R_FREE,
        beta_unleveraged=BETA_UNLEVERAGED,
        erp=ERP,
        r_debt=R_DEBT,
        equity_ratio=EQUITY_RATIO,
        debt_ratio=DEBT_RATIO,
        use_country_erp=USE_COUNTRY_ERP
    )


    # Convert to real WACC for use with annualized investment costs
    wacc_per_country['wacc_real'] = wacc_per_country['wacc'].apply(
        lambda nominal_wacc: convert_wacc_nominal_to_real(nominal_wacc, INFLATION_RATE)
    )



    print(f"\nUsing inflation rate of {INFLATION_RATE:.1%} for real WACC calculation")
    print("For annualized investment costs, use the 'wacc_real' column")

    # Show country converter map information
    show_country_map_info(output_path)

    # Save results
    wacc_per_country.to_csv(output_path / "wacc_per_country_crp.csv", index=False)
    print(f"\nSaved WACC results to {output_path / 'wacc_per_country_crp.csv'}")

    #query("country_code in ['DEU','EGY','KEN','MAR','NAM','ZAF','TUN']").round(3)\

    print(country_data.query("country_iso3 in ['DEU','EGY','KEN','MAR','NAM','ZAF','TUN']")) #Egypt, Kenya, Morocco, Namibia, South Africa and Tunisia ['CHL','ZAF','EGY','MAR','KEN','DEU']

    ct_list = ['EGY','NAM','MAR','ZAF','KEN','ETH','COD','TZA','GHA','TUN','NGA','DZA','MRT']

    # Add Mauritania (MRT) using average values from the other ct_list countries
    # Note, that this is a very rough estimate and should ideally be replaced with actual data for Mauritania when available.
    ct_list_excl_mrt = [c for c in ct_list if c != 'MRT']
    if 'MRT' not in wacc_per_country['country_code'].values:
        mrt_avg = wacc_per_country[wacc_per_country['country_code'].isin(ct_list_excl_mrt)].mean(numeric_only=True)
        mrt_row = mrt_avg.to_dict()
        mrt_row['country_code'] = 'MRT'
        mrt_row['country_name'] = 'Mauritania'
        wacc_per_country = pd.concat([wacc_per_country, pd.DataFrame([mrt_row])], ignore_index=True)
        print("Added Mauritania (MRT) using average values from ct_list countries")
    else:
        print("MRT already present in wacc_per_country")

    # Display summary
    print("\nWACC Summary:")


    # print(wacc_per_country.query(f"country_code in {ct_list}")[["country_name", "country_risk_premium", "wacc", "wacc_real"]].style.format({"country_risk_premium": "{:.2%}", "wacc": "{:.2%}", "wacc_real": "{:.2%}"}).hide(axis="index").to_latex().replace("%", "\\%"))


    print(wacc_per_country.query(
        f"country_code in {ct_list}")[["country_name", "country_code", "wacc_real"]].round(4)
    )




    print(wacc_per_country.query(
        f"country_code in {ct_list}" #['EGY','NAM','MAR','ZAF','KEN','ETH','COD','TZA','GHA','TUN','NGA','DZA','MRT']
        )[["wacc_real"]].mean())
# ['EGY','KEN','MAR','NAM','ZAF','TUN']


    # cost_of_equity = 0.045 + 2.05*1.058 * 0.065 + 0.0951
    # cost_of_debt = 0.05 * (1-0.3)
    # print(cost_of_equity*0.4+cost_of_debt*0.6)