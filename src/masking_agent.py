import pandas as pd
from sqlalchemy import create_engine
import config

def mask_data_with_groq(bronze_db_uri):
    """
    Carefully masks only required PII fields based on schema data types
    and configured keywords. Avoids masking relational IDs, categorical types, and metrics.
    """
    try:
        # 1. Read Bronze Data
        engine = create_engine(bronze_db_uri)
        df = pd.read_sql(f"SELECT * FROM {config.TABLE_NAME}", engine)
        engine.dispose()  # Prevent SQLite database locks on Windows

        # 2. Apply Masking Logic
        for col in df.columns:
            col_lower = col.lower()
            
            # SAFEGUARD 1: Protect Categorical Dimensions, Metrics, and IDs
            # E.g., 'AccountType' contains 'type', so it skips masking.
            if any(safe_key in col_lower for safe_key in config.SAFEGUARD_KEYWORDS):
                continue
                
            # SAFEGUARD 2: Protect natively typed numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
                
            # SAFEGUARD 3: Protect boolean or datetime objects
            if pd.api.types.is_bool_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            
            # 3. Check column name against our defined PII mapping
            # Uses dict order to match specific terms before broad terms
            for pii_key, mask_value in config.PII_COLUMNS_MAP.items():
                if pii_key in col_lower:
                    # Overwrite the entire column with the specific mask placeholder
                    df[col] = mask_value
                    break

        # 4. Write Sanitized Data to Gold DB
        gold_engine = create_engine(config.GOLD_DB_URI)
        df.to_sql(config.TABLE_NAME, gold_engine, if_exists="replace", index=False)
        gold_engine.dispose()  # Prevent SQLite database locks on Windows
        
        return True
        
    except Exception as e:
        print(f"Masking Pipeline Error: {e}")
        return False