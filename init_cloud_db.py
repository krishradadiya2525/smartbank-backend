import mysql.connector

# Paste your 5 Aiven details here:
DB_HOST = "mysql-4764fc2-radadiyakrish246-85f.k.aivencloud.com"          # e.g., mysql-xxxx-xxxx.aivencloud.com
DB_PORT = 16716                 # Your Aiven 5-digit port (as an integer)
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_dwjM-OX-bEbVX4iEdp5"
DB_NAME = "defaultdb"

sql_queries = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        pin VARCHAR(255) NOT NULL,
        phone VARCHAR(20),
        is_active TINYINT(1) DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        account_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        account_number VARCHAR(20) UNIQUE NOT NULL,
        account_type VARCHAR(50) DEFAULT 'Savings',
        balance DECIMAL(15, 2) DEFAULT 0.00,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        account_id INT NOT NULL,
        transaction_type VARCHAR(20) NOT NULL,
        sender_account_id INT,
        receiver_account_id INT,
        amount DECIMAL(15, 2) NOT NULL,
        category VARCHAR(50) DEFAULT 'General',
        description VARCHAR(255),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS virtual_cards (
        card_id INT AUTO_INCREMENT PRIMARY KEY,
        account_id INT NOT NULL,
        card_number VARCHAR(16) UNIQUE NOT NULL,
        cvv VARCHAR(4) NOT NULL,
        expiry_date VARCHAR(10) NOT NULL,
        is_frozen TINYINT(1) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bill_payments (
        payment_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        account_id INT NOT NULL,
        biller_name VARCHAR(100) NOT NULL,
        biller_type VARCHAR(50) NOT NULL,
        consumer_number VARCHAR(100),
        amount DECIMAL(15, 2) NOT NULL,
        status VARCHAR(20) DEFAULT 'SUCCESS',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS fixed_deposits (
        fd_id INT AUTO_INCREMENT PRIMARY KEY,
        account_id INT NOT NULL,
        deposit_amount DECIMAL(15, 2) NOT NULL,
        interest_rate DECIMAL(5, 2) NOT NULL,
        tenure_months INT NOT NULL,
        maturity_amount DECIMAL(15, 2) NOT NULL,
        status VARCHAR(20) DEFAULT 'ACTIVE',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS beneficiaries (
        beneficiary_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        beneficiary_account_number VARCHAR(20) NOT NULL,
        beneficiary_name VARCHAR(100) NOT NULL,
        bank_name VARCHAR(100) DEFAULT 'SmartBank',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """
]

def initialize_database():
    try:
        print("Connecting to Aiven Cloud Database...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        print("Connected successfully! Creating tables...")

        for query in sql_queries:
            cursor.execute(query)
            
        conn.commit()
        cursor.close()
        conn.close()
        print("All 7 tables created successfully in your Cloud Database!")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    initialize_database()