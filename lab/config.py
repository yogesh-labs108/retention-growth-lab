from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "lab.duckdb"
SQL_DIR = ROOT / "sql"
OUTPUTS = ROOT / "outputs"

DATASET_URL = "https://huggingface.co/datasets/attik/Instacart-Market-Basket-Analysis/resolve/main/{name}"
RAW_FILES = [
    "aisles.csv",
    "departments.csv",
    "products.csv",
    "orders.csv",
    "order_products__train.csv",
    "order_products__prior.csv",
]

# Instacart caps days_since_prior_order at 30, so 30 means "30 or more days".
LAPSE_DAYS = 30
