import pandas as pd
from faker import Faker
from sqlalchemy import create_engine
import random
import config
import os

def generate_bronze_data(num_records=15):
    """Generates synthetic sensitive financial records and saves to Bronze DB."""
    fake = Faker()
    data = []
    regions = ["NA", "EU", "APAC", "LATAM"]
    categories = ["Tech", "Retail", "Healthcare", "Travel"]
    
    for _ in range(num_records):
        data.append({
            "Transaction_ID": fake.uuid4(),
            "Customer_Name": fake.name(),
            "Email": fake.email(),
            "SSN": fake.ssn(),
            "Credit_Card_Number": fake.credit_card_number(),
            "Transaction_Amount": round(random.uniform(50.0, 5000.0), 2),
            "Merchant_Category": random.choice(categories),
            "Region": random.choice(regions)
        })
        
    df = pd.DataFrame(data)
    
    # Ensure data directory exists if writing directly there
    os.makedirs('data', exist_ok=True)
    engine = create_engine(config.BRONZE_DB_URI)
    df.to_sql(config.TABLE_NAME, engine, if_exists="replace", index=False)
    return df