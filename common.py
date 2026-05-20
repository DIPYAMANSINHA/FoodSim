"""
Shared constants, distributions, and loaders for the hyper-local food
delivery simulation.

The simulation logic itself lives in step1.py and step2.py. This module
holds anything that is identical across both steps: file paths, vehicle
speeds, FBO and customer point counts, and the empirical distributions
derived from the worker survey in Kolkata.
"""

from pathlib import Path
import pandas as pd

# --- File locations (relative to project root) ---
DATA_DIR = Path(__file__).parent / "data"
CUST_FBO_OD_FILE = DATA_DIR / "Cust_fboOD_rankwise.xlsx"
FBO_FBO_OD_FILE = DATA_DIR / "fbo_fboOD.xlsx"
CUSTOMER_OD_FILE = DATA_DIR / "CustomerOD_rankwise.csv.gz"
DISTRIBUTIONS_FILE = DATA_DIR / "distributions.csv"

# --- Simulation grid sizes ---
N_FBOS = 102           # Number of food business outlets (FBOs)
N_CUSTOMER_POINTS = 1800  # Number of customer demand points in the study area

# --- Vehicle speeds (km/h), empirically derived ---
MOTORBIKE_KMH = 19.67
BICYCLE_KMH = 12.0

# --- Pay structure (INR), as in Sinha & Pandit (2023) ---
# Wage rate (per km of travel) is configurable per scenario, not fixed here.
CUSTOMER_PAY_PER_ORDER = 5     # Flat INR per order
WAIT_TIME_PAY_PER_MIN = 1      # INR per minute of waiting at FBO


def load_distributions():
    """
    Load the four empirical distributions used to generate synthetic orders
    and worker characteristics.

    Returns
    -------
    dict
        Keys: 'fbo_popularity', 'order_hour', 'wait_time_minutes', 'work_hours'
        Each value is a pandas Series indexed by the discrete value, with
        probability as the value. Use `.index.to_numpy()` for the support
        and `.values` for probabilities when calling numpy.random.choice.
    """
    df = pd.read_csv(DISTRIBUTIONS_FILE)
    out = {}
    for name, group in df.groupby("distribution"):
        out[name] = group.set_index("index")["probability"]
    return out


def load_distance_matrices():
    """
    Load the three GIS-derived shortest-path distance matrices.

    Returns
    -------
    tuple of pandas DataFrames
        (cust_fbo_df, fbo_fbo_df, customer_df)
        - cust_fbo_df: rows indexed by (fbo * N_CUSTOMER_POINTS + customer);
          'Total_Length' column in km.
        - fbo_fbo_df: rows indexed by (fbo1 * N_FBOS + fbo2);
          'Total_Length' column in km.
        - customer_df: rows indexed by (customer1 * N_CUSTOMER_POINTS + customer2);
          'Total_Length' column in METRES (divide by 1000 for km).
    """
    cust_fbo_df = pd.read_excel(CUST_FBO_OD_FILE, sheet_name="Cust_fboOD_rankwise")
    fbo_fbo_df = pd.read_excel(FBO_FBO_OD_FILE, sheet_name="fbo_fboOD")
    customer_df = pd.read_csv(CUSTOMER_OD_FILE)  # pandas reads .gz natively
    customer_df.sort_values(
        ["OriginID", "DestinationID"], ascending=[True, True], inplace=True
    )
    return cust_fbo_df, fbo_fbo_df, customer_df