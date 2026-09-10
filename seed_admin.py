import mysql.connector
import bcrypt

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'smartbank_db',
    'port': 3306
}

def create_admin():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    email = "admin@smartbank.com"
    raw_password = "admin123".encode('utf-8')
    raw_pin = "0000".encode('utf-8')

    # Hash password and pin using bcrypt
    hashed_pw = bcrypt.hashpw(raw_password, bcrypt.gensalt()).decode('utf-8')
    hashed_pin = bcrypt.hashpw(raw_pin, bcrypt.gensalt()).decode('utf-8')

    try:
        # Remove any existing admin account to avoid duplicates
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        
        # Insert admin user with role 'ADMIN'
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, pin_hash, role) VALUES (%s, %s, %s, %s, 'ADMIN')",
            ("System Admin", email, hashed_pw, hashed_pin)
        )
        db.commit()
        print("\n✅ Admin account created successfully!")
        print("------------------------------------------")
        print("Email:    admin@smartbank.com")
        print("Password: admin123\n")
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin: {e}")
    finally:
        cursor.close()
        db.close()

if __name__ == '__main__':
    create_admin()