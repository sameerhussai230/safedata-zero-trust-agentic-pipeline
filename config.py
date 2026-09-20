import os

# --- LLM Configuration ---
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE = 0.0
LLM_SUGGESTION_TEMP = 0.3 

# --- Database Configuration ---
GOLD_DB_URI = "sqlite:///gold.db"
BRONZE_DB_URI = "sqlite:///bronze.db"
TABLE_NAME = "transactions"

# --- Application Constraints ---
MAX_ROWS_UPLOAD = 100

# --- PII Masking Configuration ---
# NOTE: Order matters! Put specific words (like 'holder') before generic ones (like 'account')
PII_COLUMNS_MAP = {
    "name": "[MASKED_NAME]",
    "holder": "[MASKED_NAME]",  # Catches AccountHolder
    "email": "[MASKED_EMAIL]",
    "ssn": "[MASKED_SSN]",
    "credit": "[MASKED_CREDIT_CARD]",
    "card": "[MASKED_CREDIT_CARD]",
    "phone": "[MASKED_PHONE]",
    "address": "[MASKED_ADDRESS]",
    "account": "[MASKED_ACCOUNT]" # Placed last to avoid overriding 'AccountHolder'
}

# --- Analytics Safeguards ---
# Columns containing these substrings will NEVER be masked, 
# ensuring groupings and metrics remain intact for Text-to-SQL.
SAFEGUARD_KEYWORDS = [
    "type", "category", "status", "id", "amount", 
    "balance", "code", "date", "region", "department", 
    "quantity", "price", "city", "state", "country"
]