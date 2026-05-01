# Calculation of Weighted Average Cost of Capital (WACC)

from __future__ import annotations
import logging
import pandas as pd
import country_converter as coco
from pathlib import Path
from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)

# Default values for missing country data
CRP = float('nan')  # NaN for missing country risk premium
TAX = float('nan')  # NaN for missing corporate tax rate

# Damodaran source column names (double-space is intentional — matches HTML table headers)
COL_COUNTRY = "Country"
COL_CRP     = "Country Risk  Premium"
COL_TAX     = "Corporate Tax  Rate"
COL_SPREAD  = "Adj. Default  Spread"
COL_ERP     = "Equity Risk  Premium"
COL_RATING  = "Moody's rating"


class WaccParams(BaseModel):
    """Financial parameters for WACC calculation. All rates as decimals (e.g. 3.5 % → 0.035)."""

    model_config = ConfigDict(frozen=True)

    r_free: float = 0.035          # Risk-free rate
    beta: float = 1.1              # Unleveraged beta (Green & Renewable Energy, Damodaran)
    erp: float = 0.065             # Equity risk premium
    swap_rate: float = 0.030       # SWAP benchmark rate
    debt_spread: float = 0.020     # Credit spread over SWAP
    r_debt: float = 0.050          # Total cost of debt (swap_rate + debt_spread)
    equity_ratio: float = 0.40     # Share of equity financing
    debt_ratio: float = 0.60       # Share of debt financing
    inflation_rate: float = 0.020  # Expected annual inflation
    use_country_erp: bool = False  # Use country-specific ERP when available

    @model_validator(mode='after')
    def check_capital_structure(self) -> WaccParams:
        if abs(self.equity_ratio + self.debt_ratio - 1.0) > 1e-9:
            raise ValueError(
                f"equity_ratio + debt_ratio must equal 1.0, got {self.equity_ratio + self.debt_ratio:.6f}"
            )
        return self


def parse_percentage(value: object, default: float | None = None) -> float | None:
    """Parse a percentage string or numeric value to a decimal float (e.g. '9.51%' → 0.0951)."""
    if pd.isna(value) or str(value).lower().strip() in ['nan', 'none', '']:
        return default
    try:
        return float(str(value).replace('%', '').strip()) / 100
    except (ValueError, TypeError):
        return default


def parse_string(value: object) -> str | None:
    """Parse a value to a stripped string, or None if empty/NaN."""
    if pd.isna(value) or str(value).lower().strip() in ['nan', 'none', '']:
        return None
    return str(value).strip()


def download_country_risk_premium(output_path: Path, skip_download: bool = False) -> pd.DataFrame | None:
    """
    Download country risk premium data from Damodaran's website
    
    Parameters:
    output_path (Path): Path to save output files
    skip_download (bool): If True, skip download and use fallback data immediately
    """
    if skip_download:
        logger.info("Skipping download, using fallback data...")
        fallback_path = output_path / "country_risk_premium_raw.csv"
        try:
            crp_data_raw = pd.read_csv(fallback_path)
            logger.info(f"Using fallback data from {fallback_path}")
            return crp_data_raw
        except FileNotFoundError:
            logger.warning(f"Fallback file {fallback_path} not found. Proceeding with download...")
    
    try:
        url = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html"

        logger.info(f"Downloading country risk premium data from {url}...")
        table = pd.read_html(url, header=0)[1] # Skip the first table which is not relevant
        
        if len(table) > 150 and COL_CRP in table.columns:
            crp_data_raw = table  
            crp_data_raw.to_csv(output_path / "country_risk_premium_raw.csv", index=False)
            logger.info(f"Saved country risk premium data with {len(table)} rows and columns: {list(crp_data_raw.columns)}")
            return crp_data_raw
        else: 
            raise ValueError("Unexpected table format or data rows.")        
        
    except Exception as e:
        logger.error(f"Error downloading country risk premium data: {e}")

        fallback_path = output_path / "country_risk_premium_raw.csv"
        crp_data_raw = pd.read_csv(fallback_path)
        logger.info(f"Falling back to using {fallback_path}")

        return crp_data_raw

def create_country_converter_map(output_path: Path, crp_data_raw: pd.DataFrame) -> dict[str, str]:
    """
    Create and save a country converter map for consistent country code conversion
    
    Parameters:
    output_path (Path): Path to save output files
    crp_data_raw (pd.DataFrame): Raw country risk premium data
    
    Returns:
    dict: Country name to ISO3 code mapping
    """
    logger.info("Creating country converter map...")
    
    # Get column name for country
    country_col = COL_COUNTRY if COL_COUNTRY in crp_data_raw.columns else crp_data_raw.columns[0]
    
    # Extract unique country names
    country_names = crp_data_raw[country_col].dropna().astype(str).str.strip().unique()
    country_names = [name for name in country_names if name.lower() not in ['nan', 'none', '']]
    
    # Create mapping
    country_map = {}
    conversion_issues = []
    
    for country_name in country_names:
        try:
            country_code = coco.convert(country_name, to='ISO3')
            if isinstance(country_code, list) or country_code == 'not found':
                # coco.convert returns a list when a name matches multiple countries
                logger.warning(f"Ambiguous or unresolved country name (skipping): {country_name!r} → {country_code}")
                conversion_issues.append(country_name)
                country_map[country_name] = None  # Mark for manual review
            else:
                country_map[country_name] = country_code
        except Exception as e:
            logger.error(f"Error converting {country_name}: {e}")
            conversion_issues.append(country_name)
            country_map[country_name] = None
    
    # Create DataFrame and save
    map_df = pd.DataFrame([
        {'country_name': name, 'iso3_code': code, 'needs_review': code is None}
        for name, code in country_map.items()
    ])
    
    map_file = output_path / "country_converter_map.csv"
    map_df.to_csv(map_file, index=False)
    
    logger.info(f"Saved country converter map to {map_file}")
    logger.info(f"Successfully converted {len([c for c in country_map.values() if c is not None])} countries")
    
    if conversion_issues:
        logger.warning(f"Found {len(conversion_issues)} countries needing manual review:")
        for issue in conversion_issues[:10]:  # Show first 10
            logger.warning(f"  - {issue}")
        if len(conversion_issues) > 10:
            logger.warning(f"  ... and {len(conversion_issues) - 10} more")
        logger.warning("Please review and manually correct the country_converter_map.csv file")
    
    return country_map

def load_country_converter_map(output_path: Path) -> dict[str, str] | None:
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
        
        # Exclude NaN, empty strings, and list-like values (e.g. "['PRK', 'KOR']")
        valid = map_df[
            map_df['iso3_code'].notna()
            & (map_df['iso3_code'] != '')
            & ~map_df['iso3_code'].astype(str).str.startswith('[')
        ]
        country_map = valid.set_index('country_name')['iso3_code'].to_dict()
        
        logger.info(f"Loaded country converter map with {len(country_map)} valid mappings")
        return country_map
        
    except Exception as e:
        logger.error(f"Error loading country converter map: {e}")
        return None

def show_country_map_info(output_path: Path) -> None:
    """
    Display information about the current country converter map
    
    Parameters:
    output_path (Path): Path where output files are saved
    """
    map_file = output_path / "country_converter_map.csv"
    
    if not map_file.exists():
        logger.warning("No country converter map found")
        return
    
    try:
        map_df = pd.read_csv(map_file)
        total_countries = len(map_df)
        valid_mappings = len(map_df[map_df['iso3_code'].notna() & (map_df['iso3_code'] != '')])
        needs_review = len(map_df[map_df['needs_review'] == True])
        
        logger.info(f"Country Converter Map: {total_countries} total, {valid_mappings} valid, {needs_review} needs review")
        
        if needs_review > 0:
            review_countries = map_df[map_df['needs_review'] == True]['country_name'].tolist()
            shown = ', '.join(review_countries[:5])
            extra = f" ... and {len(review_countries) - 5} more" if len(review_countries) > 5 else ""
            logger.warning(f"Countries needing review: {shown}{extra}")
        
    except Exception as e:
        logger.error(f"Error reading country converter map: {e}")

def process_country_risk_premium(output_path: Path, crp_data_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Process and clean up country-specific risk premiums and tax rates from downloaded data
    Uses saved country converter map for consistent country code conversion
    
    Parameters:
    output_path (Path): Path where output files are saved
    crp_data_raw (pd.DataFrame): Raw country risk premium data
    """
    logger.info("Processing country-specific data...")
    
    # Load or create country converter map
    country_map = load_country_converter_map(output_path)
    if country_map is None:
        logger.info("No existing country converter map found, creating new one...")
        country_map = create_country_converter_map(output_path, crp_data_raw)
    else:
        logger.info("Using existing country converter map")
    
    crp_data = {}
    
    if crp_data_raw is not None and len(crp_data_raw) > 1:
        try:
            # Column mapping — prefer named constants, fall back to positional index
            cols = {
                'country': COL_COUNTRY if COL_COUNTRY in crp_data_raw.columns else crp_data_raw.columns[0],
                'crp': COL_CRP if COL_CRP in crp_data_raw.columns else crp_data_raw.columns[3],
                'tax': COL_TAX if COL_TAX in crp_data_raw.columns else crp_data_raw.columns[4],
                'adj_spread': COL_SPREAD if COL_SPREAD in crp_data_raw.columns else None,
                'erp': COL_ERP if COL_ERP in crp_data_raw.columns else None,
                'rating': COL_RATING if COL_RATING in crp_data_raw.columns else None,
            }
            
            for _, row in crp_data_raw.iterrows():
                country_name_raw = str(row[cols['country']]).strip()
                
                if not country_name_raw or country_name_raw.lower() in ['nan', 'none', '']:
                    continue
                
                try:
                    # Use the saved country converter map
                    country_code = country_map.get(country_name_raw)
                    
                    if country_code is None:
                        logger.warning(f"Country not in converter map (skipping): {country_name_raw}")
                        continue
                    
                    crp_data[country_code] = {
                        'country_risk_premium': parse_percentage(row[cols['crp']], CRP),
                        'tax_rate': parse_percentage(row[cols['tax']], TAX),
                        'country_name': country_name_raw,
                        'adj_default_spread': parse_percentage(row[cols['adj_spread']]) if cols['adj_spread'] else None,
                        'equity_risk_premium': parse_percentage(row[cols['erp']]) if cols['erp'] else None,
                        'moodys_rating': parse_string(row[cols['rating']]) if cols['rating'] else None,
                    }
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing data for {country_name_raw}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing downloaded data: {e}")
            logger.error("No country data could be processed")
    else:
        logger.warning("No valid CRP data available")
    
    crp_data_df = pd.DataFrame.from_dict(crp_data, orient='index')
    crp_data_df.index.name = 'country_iso3'
    
    crp_data_df.to_csv(output_path / "crp_data.csv", index=True)
    logger.info(f"Saved country parameters for {len(crp_data_df)} countries to {output_path / 'crp_data.csv'}")
    
    return crp_data_df


def download_beta_data(output_path: Path, skip_download: bool = False) -> pd.DataFrame | None:
    """
    Download beta data from Damodaran's website. 
    Note: Beta factors could also be calculated based on comparing specific power-to-X or renewables index with S&P 500 or MSCI World Index.
    
    Parameters:
    output_path (Path): Path to save output files
    skip_download (bool): If True, skip download and use fallback data immediately
    """
    if skip_download:
        logger.info("Skipping beta data download, using fallback data...")
        fallback_path = output_path / "industry_beta_raw.csv"
        try:
            beta_data = pd.read_csv(fallback_path)
            logger.info(f"Using fallback beta data from {fallback_path}")
            return beta_data
        except FileNotFoundError:
            logger.warning(f"Fallback file {fallback_path} not found. Proceeding with download...")
    
    try:
        url = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html"
        logger.info("Downloading beta data...")
        
        tables = pd.read_html(url)
        
        # Find the industry beta table - typically the largest table with industry names
        beta_data = None
        for i, table in enumerate(tables):
            if len(table) > 150:  # Industry table should have many rows and columns
                # Check if first column contains industry names
                first_col_sample = table.iloc[1:6, 0].astype(str).str.lower()
                if any(industry in ' '.join(first_col_sample) for industry in ['energy', 'renewable', 'oil', 'utility']):
                    beta_data = table
                    logger.info(f"Found beta table (table {i}) with {len(table)} rows")
                    break
                    
        if beta_data is None:
            # Fallback to largest table
            beta_data = max(tables, key=len) if tables else None
            if beta_data is not None:
                logger.warning("Using largest table as fallback for beta data")
            else:
                logger.warning("No beta tables found")
            
        if beta_data is not None:
            # Save the raw data
            beta_data.to_csv(output_path / "industry_beta_raw.csv", index=False)
            logger.info(f"Saved beta data with columns: {list(beta_data.columns)}")
        
        return beta_data
        
    except Exception as e:
        logger.error(f"Error downloading beta data: {e}")
        return None



def calculate_wacc(
    r_free: float,
    beta: float,
    erp: float,
    crp: float,
    r_debt: float,
    tax: float,
    equity_ratio: float,
    debt_ratio: float,
) -> float:
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

def calculate_wacc_per_country(
    country_data: pd.DataFrame,
    r_free: float,
    beta_unleveraged: float,
    erp: float,
    r_debt: float,
    equity_ratio: float,
    debt_ratio: float,
    use_country_erp: bool = False,
) -> pd.DataFrame:
    """
    Calculate WACC for each country using country-specific parameters.

    Parameters:
    use_country_erp (bool): If True, use country-specific equity risk premium when available,
                           otherwise use the global ERP value
    """
    logger.info("Calculating WACC per country...")
    if use_country_erp:
        logger.info("Using country-specific equity risk premium when available")

    df = country_data.copy()

    # Effective ERP: country-specific where available and requested, else global value
    if use_country_erp:
        df['_erp'] = df['equity_risk_premium'].where(df['equity_risk_premium'].notna(), erp)
    else:
        df['_erp'] = erp

    # Hamada re-levering: β_L = β_U · (1 + (1−T) · w_d / w_e)
    df['beta'] = beta_unleveraged * (1 + (1 - df['tax_rate']) * debt_ratio / equity_ratio)

    # CAPM + CRP cost of equity; after-tax cost of debt
    cost_of_equity = r_free + df['beta'] * df['_erp'] + df['country_risk_premium']
    cost_of_debt = r_debt * (1 - df['tax_rate'])
    df['wacc'] = cost_of_equity * equity_ratio + cost_of_debt * debt_ratio

    return pd.DataFrame({
        'country_code': df.index,
        'country_name': df['country_name'],
        'wacc': df['wacc'],
        'risk_free_rate': r_free,
        'beta': df['beta'],
        'equity_risk_premium': df['_erp'],
        'country_risk_premium': df['country_risk_premium'],
        'debt_rate': r_debt,
        'tax_rate': df['tax_rate'],
        'equity_ratio': equity_ratio,
        'debt_ratio': debt_ratio,
    })

def convert_wacc_nominal_to_real(nominal_wacc: float, inflation_rate: float) -> float:
    """
    Convert nominal WACC to real WACC
    
    Parameters:
    nominal_wacc (float): Nominal WACC rate
    inflation_rate (float): Expected inflation rate
    
    Returns:
    float: Real WACC rate
    """
    return (1 + nominal_wacc) / (1 + inflation_rate) - 1

def convert_wacc_real_to_nominal(real_wacc: float, inflation_rate: float) -> float:
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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    output_path = Path(__file__).resolve().parent.parent / "data"
    output_path.mkdir(parents=True, exist_ok=True)
    results_path = Path(__file__).resolve().parent.parent / "results"
    results_path.mkdir(parents=True, exist_ok=True)

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

    params = WaccParams(
        r_free=0.035,
        beta=1.1,        # source: Damodaran Betas.html → Green & Renewable Energy
        erp=0.10 - 0.035,  # nominal long-term market return minus risk-free rate
        swap_rate=0.030,
        debt_spread=0.020,
        r_debt=0.03 + 0.02,  # SWAP rate + credit margin
        equity_ratio=0.40,
        debt_ratio=0.60,
        inflation_rate=0.02,
        use_country_erp=False,  # set True to use country-specific ERP when available
    )

    # Calculate nominal WACC per country
    wacc_per_country = calculate_wacc_per_country(
        country_data=country_data,
        r_free=params.r_free,
        beta_unleveraged=params.beta,
        erp=params.erp,
        r_debt=params.r_debt,
        equity_ratio=params.equity_ratio,
        debt_ratio=params.debt_ratio,
        use_country_erp=params.use_country_erp,
    )

    # Convert to real WACC for use with annualized investment costs
    wacc_per_country['wacc_real'] = wacc_per_country['wacc'].apply(
        lambda nominal_wacc: convert_wacc_nominal_to_real(nominal_wacc, params.inflation_rate)
    )



    print(f"\nUsing inflation rate of {params.inflation_rate:.1%} for real WACC calculation")
    print("For annualized investment costs, use the 'wacc_real' column")

    # Show country converter map information
    show_country_map_info(output_path)

    # Add Mauritania (MRT) using average values from the other ct_list countries
    # Note, that this is a very rough estimate and should ideally be replaced with actual data for Mauritania when available.
    ct_ref_list_for_mrt = ['EGY','KEN','NAM']
    if 'MRT' not in wacc_per_country['country_code'].values:
        mrt_avg = wacc_per_country[wacc_per_country['country_code'].isin(ct_ref_list_for_mrt)].mean(numeric_only=True)
        mrt_row = mrt_avg.to_dict()
        mrt_row['country_code'] = 'MRT'
        mrt_row['country_name'] = 'Mauritania'
        wacc_per_country = pd.concat([wacc_per_country, pd.DataFrame([mrt_row])], ignore_index=True)
        print(f"Added Mauritania (MRT) using average values from {ct_ref_list_for_mrt}")
    else:
        print("MRT already present in wacc_per_country")

    # Save results
    wacc_per_country.to_csv(results_path / "wacc_per_country_crp.csv", index=False)
    print(f"\nSaved WACC results to {results_path / 'wacc_per_country_crp.csv'}")

    #query("country_code in ['DEU','EGY','KEN','MAR','NAM','ZAF','TUN']").round(3)\

    # print(country_data.query("country_iso3 in ['DEU','EGY','KEN','MAR','NAM','ZAF','TUN']")) 

    # AGHA: Egypt, Kenya, Mauretania, Morocco, Namibia, South Africa


    # Display summary
    print("\nWACC Summary:")

    ct_list = ['EGY','NAM','MAR','ZAF','KEN','ETH','COD','TZA','GHA','TUN','NGA','DZA','MRT', 'OMN','SAU']
    
    #['EGY','KEN','MAR','NAM','ZAF','TUN']

    # print(wacc_per_country.query(f"country_code in {ct_list}")[["country_name", "country_risk_premium", "wacc", "wacc_real"]].style.format({"country_risk_premium": "{:.2%}", "wacc": "{:.2%}", "wacc_real": "{:.2%}"}).hide(axis="index").to_latex().replace("%", "\\%"))


    print(wacc_per_country.query(
        f"country_code in {ct_list}")[["country_name", "country_code", "wacc_real", "wacc"]].round(4)
    )




    print(wacc_per_country.query(
        f"country_code in {ct_list}" 
        )[["wacc_real"]].mean())



    # cost_of_equity = 0.045 + 2.05*1.058 * 0.065 + 0.0951
    # cost_of_debt = 0.05 * (1-0.3)
    # print(cost_of_equity*0.4+cost_of_debt*0.6)