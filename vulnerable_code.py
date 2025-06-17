 
import mysql.connector
from flask import request, jsonify

# Vulnerable authentication function
def authenticate(username, password):
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    
    # Hardcoded database credentials
    conn = mysql.connector.connect(
        host="localhost",
        user="admin",
        password="admin123",  # Hardcoded password
        database="userdb"
    )
    
    cursor = conn.cursor()
    cursor.execute(query)  # Direct execution of user input
    
    return cursor.fetchone()

# API endpoint with multiple issues
def process_payment():
    amount = request.args.get('amount')
    card = request.args.get('card')
    
    # No input validation
    # Missing authentication check
    
    # Hardcoded API key
    API_KEY = "sk-prod-4242424242424242"
    
    # Process all transactions (performance issue)
    all_transactions = get_all_transactions()
    for transaction in all_transactions:
        for item in transaction.items:
            # Nested loops - O(n²)
            validate_item(item)
    
    # Inefficient string concatenation
    log = ""
    for i in range(1000):
        log += f"Processing step {i}\n"
    
    return {"status": "success", "log": log}

# Missing docstrings throughout
class PaymentProcessor:
    def __init__(self):
        self.key = "secret123"  # Hardcoded secret
    
    def process(self, data):
        # No error handling
        # No input validation
        return self.external_api_call(data)