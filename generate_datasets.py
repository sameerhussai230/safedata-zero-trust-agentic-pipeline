import pandas as pd
import sqlite3
import os
import random
from faker import Faker

os.makedirs('data', exist_ok=True)
fake = Faker()
Faker.seed(42)
random.seed(42)

def generate_ecommerce():
    data = [{
        "order_id": fake.uuid4()[:8],
        "customer_name": fake.name(),
        "customer_email": fake.email(),
        "category": random.choice(["Electronics", "Apparel", "Home Goods", "Toys"]),
        "order_amount": round(random.uniform(20.0, 500.0), 2)
    } for _ in range(50)]
    pd.DataFrame(data).to_sql("transactions", sqlite3.connect("data/bronze_ecommerce.db"), if_exists="replace", index=False)

def generate_healthcare():
    data = [{
        "patient_id": fake.uuid4()[:8],
        "patient_name": fake.name(),
        "ssn": fake.ssn(),
        "department": random.choice(["Cardiology", "Neurology", "Orthopedics", "Pediatrics"]),
        "diagnosis_code": random.choice(["I10", "E11", "J45", "M54"]),
        "bill_amount": round(random.uniform(100.0, 5000.0), 2)
    } for _ in range(50)]
    pd.DataFrame(data).to_sql("transactions", sqlite3.connect("data/bronze_healthcare.db"), if_exists="replace", index=False)

def generate_banking():
    data = [{
        "account_id": fake.iban(),
        "account_holder": fake.name(),
        "credit_card": fake.credit_card_number(),
        "account_type": random.choice(["Checking", "Savings", "Investment", "Credit"]),
        "balance": round(random.uniform(500.0, 50000.0), 2)
    } for _ in range(50)]
    pd.DataFrame(data).to_sql("transactions", sqlite3.connect("data/bronze_banking.db"), if_exists="replace", index=False)

def generate_all():
    """Wrapper function called by app.py on cold boot."""
    generate_ecommerce()
    generate_healthcare()
    generate_banking()
    print("✅ Synthetic datasets generated successfully!")

if __name__ == "__main__":
    generate_all()