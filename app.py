from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import bcrypt
import random
import io
import os
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from datetime import timedelta

# ---------------- 1. INITIALIZE FLASK & CORS ---------------- #
app = Flask(__name__)
CORS(app)



# Database Configuration for XAMPP (Default MySQL password is empty "")
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'smartbank_db',
    'port': 3307
}

def get_db():
    return mysql.connector.connect(
            host=os.environ.get("DB_HOST", "mysql-4764fc2-radadiyakrish246-85f.k.aivencloud.com"),
            port=int(os.environ.get("DB_PORT", 16716)),          # Your Aiven port number
            user=os.environ.get("DB_USER", "avnadmin"),
            password=os.environ.get("DB_PASSWORD", "AVNS_dwjM-OX-bEbVX4iEdp5"),
            database=os.environ.get("DB_NAME", "defaultdb"),
            ssl_disabled=False
        )

import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ================= EMAIL CONFIGURATION =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "smartbank121316@gmail.com"          # Your Gmail
SENDER_PASSWORD = "wgbp embw mwzl jyqk"           # 16-digit App Password

def send_transaction_email_async(to_email, user_name, amount, current_balance, tx_type_desc, account_number, is_credit=False):
    """Sends background HTML email for DEBIT (-) and CREDIT (+) transactions."""
    def _send():
        if not to_email or "@" not in to_email:
            return

        alert_type = "Credit Alert" if is_credit else "Debit Alert"
        action_verb = "credited to" if is_credit else "debited from"
        amount_sign = "+" if is_credit else "-"
        amount_color = "#2E7D32" if is_credit else "#D32F2F"

        subject = f"{alert_type}: ${amount:.2f} {action_verb} A/C ...{str(account_number)[-4:]}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 550px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #1A237E; margin-top: 0;">SmartBank {alert_type}</h2>
                <p>Dear <b>{user_name}</b>,</p>
                <p>Your account has been <b>{action_verb}</b> for the following transaction:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px 0; color: #666;">Transaction Details:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{tx_type_desc}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px 0; color: #666;">Amount:</td>
                        <td style="padding: 8px 0; font-weight: bold; color: {amount_color};">{amount_sign}${amount:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px 0; color: #666;">Account Number:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{account_number}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px 0; color: #666;">Available Balance:</td>
                        <td style="padding: 8px 0; font-weight: bold; color: #1A237E;">${current_balance:.2f}</td>
                    </tr>
                </table>

                <p style="font-size: 12px; color: #777;">
                    {"Thank you for banking with SmartBank." if is_credit else "If this transaction was not authorized by you, please contact SmartBank support immediately."}
                </p>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SmartBank <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        except Exception as e:
            print(f"[EMAIL ERROR]: Failed sending to {to_email}: {e}")

    # Runs in a separate daemon thread so app UI does not freeze
    threading.Thread(target=_send, daemon=True).start()
    
    
# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "smartbank121316@gmail.com"
SENDER_PASSWORD = "wgbp embw mwzl jyqk"

# Directory for saving uploaded KYC documents
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def send_otp_email(target_email, otp, purpose="Verification"):
    """Sends OTP via SMTP with an HTML formatted email."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"SmartBank Security <{SENDER_EMAIL}>"
        msg['To'] = target_email
        msg['Subject'] = f"{otp} is your SmartBank {purpose} Code"

        body = f"""
        <h2>SmartBank Security</h2>
        <p>Your One-Time Password (OTP) for SmartBank <b>{purpose.lower()}</b> is:</p>
        <h1 style="color: #3F51B5; letter-spacing: 4px;">{otp}</h1>
        <p>This code is valid for <b>10 minutes</b>. Do not share this code with anyone.</p>
        <br/>
        <p>Regards,<br/>SmartBank Security Team</p>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, target_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[EMAIL SEND ERROR]: {e}")
        return False

# ---------------- FORGOT PASSWORD ENDPOINTS ---------------- #

@app.route('/api/auth/forgot-password/send-otp', methods=['POST'])
def forgot_password_send_otp():
    data = request.json or {}
    email = str(data.get('email', '')).strip().lower()

    if not email:
        return jsonify({"status": "error", "message": "Email address is required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # 1. Verify user exists
        cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "No account registered with this email"}), 404

        # 2. Generate 6-digit OTP & Expiry (10 minutes)
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now() + timedelta(minutes=10)

        # 3. Store OTP in database
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
        cursor.execute("""
            INSERT INTO otp_verifications (email, otp_code, expires_at)
            VALUES (%s, %s, %s)
        """, (email, otp_code, expires_at))
        db.commit()

        # 4. Dispatch Email
        if send_otp_email(email, otp_code):
            return jsonify({"status": "success", "message": "OTP has been sent to your email."}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send email. Check SMTP settings."}), 500

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@app.route('/api/auth/forgot-password/reset', methods=['POST'])
def reset_password_with_otp():
    data = request.json or {}
    email = str(data.get('email', '')).strip().lower()
    otp_code = str(data.get('otp', '')).strip()
    new_password = str(data.get('new_password', '')).strip()

    if not email or not otp_code or not new_password:
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    if len(new_password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters long"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # 1. Validate OTP from database
        cursor.execute("""
            SELECT * FROM otp_verifications 
            WHERE email = %s AND otp_code = %s AND expires_at > NOW()
        """, (email, otp_code))
        otp_record = cursor.fetchone()

        if not otp_record:
            return jsonify({"status": "error", "message": "Invalid or expired OTP"}), 400

        # 2. Hash New Password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

        # 3. Update Password
        cursor.execute("UPDATE users SET password_hash = %s WHERE LOWER(email) = %s", (hashed_password, email))

        # 4. Clear used OTP
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
        db.commit()

        return jsonify({"status": "success", "message": "Password reset successfully! Please login."}), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()


# ---------------- USER REGISTRATION WITH KYC & SALARY ---------------- #

# ---------------- 1. SEND REGISTRATION OTP ---------------- #
# In-memory store for OTPs
otp_store = {}

@app.route('/api/auth/send-otp', methods=['POST'])
def send_registration_otp():
    try:
        data = request.json or {}
        email = str(data.get('email', '')).strip().lower()

        if not email or '@' not in email:
            return jsonify({"status": "error", "message": "A valid email address is required"}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True, buffered=True)
        try:
            # Check if email is already registered
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s", (email,))
            if cursor.fetchone():
                return jsonify({"status": "error", "message": "Email is already registered. Please login."}), 400

            otp_code = str(random.randint(100000, 999999))
            otp_store[email] = otp_code
            print(f"[DEBUG REGISTER OTP] Email: '{email}' | OTP: '{otp_code}'")

            if send_otp_email(email, otp_code, purpose="Registration Verification"):
                return jsonify({"status": "success", "message": f"OTP sent successfully to {email}"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send email. Check SMTP settings."}), 500
        finally:
            cursor.close()
            db.close()
    except Exception as e:
        print(f"[SEND OTP ERROR]: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


# ---------------- 2. REGISTER WITH KYC & OTP VALIDATION ---------------- #

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    try:
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        pin = request.form.get('pin', '').strip()
        user_otp = request.form.get('otp', '').strip()
        salary = float(request.form.get('salary', 0.0))

        if not full_name or not email or not password or len(pin) != 4 or not user_otp:
            return jsonify({"status": "error", "message": "All fields including OTP and 4-digit PIN are required"}), 400

        # Validate OTP
        stored_otp = otp_store.get(email)
        if not stored_otp or stored_otp != user_otp:
            return jsonify({"status": "error", "message": "Invalid or expired OTP code!"}), 400

        # Handle Document Uploads
        photo_file = request.files.get('photo')
        pan_file = request.files.get('pan')
        aadhar_file = request.files.get('aadhar')

        photo_path, pan_path, aadhar_path = None, None, None

        if photo_file:
            fname = secure_filename(f"photo_{email}_{photo_file.filename}")
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            photo_file.save(photo_path)

        if pan_file:
            fname = secure_filename(f"pan_{email}_{pan_file.filename}")
            pan_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            pan_file.save(pan_path)

        if aadhar_file:
            fname = secure_filename(f"aadhar_{email}_{aadhar_file.filename}")
            aadhar_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            aadhar_file.save(aadhar_path)

        db = get_db()
        cursor = db.cursor(dictionary=True, buffered=True)

        cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email is already registered"}), 400

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        hashed_pin = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            INSERT INTO users (full_name, email, salary, photo_url, pan_url, aadhar_url, password_hash, pin, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'USER')
        """, (full_name, email, salary, photo_path, pan_path, aadhar_path, hashed_pw, hashed_pin))
        user_id = cursor.lastrowid

        # Create account in PENDING state (inactive until approved)
        account_num = f"2000{user_id:06d}"
        cursor.execute("""
            INSERT INTO accounts (user_id, account_number, account_type, balance, status, is_active)
            VALUES (%s, %s, 'SAVINGS', 0.00, 'PENDING', 0)
        """, (user_id, account_num))

        db.commit()

        if email in otp_store:
            del otp_store[email]

        return jsonify({
            "status": "success",
            "message": "Application submitted successfully! Your account will be active within 24 working hours after admin verification."
        }), 201

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()
            
@app.route('/api/login', methods=['POST'])
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '').encode('utf-8')

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password, user['password_hash'].encode('utf-8')):
            # Fetch active accounts
            cursor.execute("SELECT * FROM accounts WHERE user_id = %s", (user['user_id'],))
            accounts = cursor.fetchall()

            # If user has no active accounts (was deleted by admin), block login
            if user['role'] != 'ADMIN' and not accounts:
                return jsonify({
                    "status": "error",
                    "message": "Your banking account has been closed or deleted. Please register for a new account."
                }), 403

            return jsonify({
                "status": "success",
                "user": {
                    "user_id": user['user_id'],
                    "full_name": user['full_name'],
                    "email": user['email'],
                    "role": user.get('role', 'USER')
                },
                "accounts": accounts
            }), 200

        return jsonify({"status": "error", "message": "Invalid email or password"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()   

#----------------------------otp function-----------------------------------#

# SENDER_EMAIL = "smartbank121316@gmail.com"  # Replace with your Gmail
# SENDER_PASSWORD = "wgbp embw mwzl jyqk"  # Replace with generated App Password

# def send_otp_email(receiver_email, otp_code):
#     try:
#         msg = MIMEMultipart()
#         msg['From'] = f"SmartBank Security <{SENDER_EMAIL}>"
#         msg['To'] = receiver_email
#         msg['Subject'] = f"{otp_code} is your SmartBank Verification Code"

#         body = f"""
#         Hello,

#         Your One-Time Password (OTP) for SmartBank transaction verification is:

#         {otp_code}

#         This code is valid for 5 minutes. Do not share this code with anyone.

#         Regards,
#         SmartBank Security Team
#         """
#         msg.attach(MIMEText(body, 'plain'))

#         # Connect to Gmail SMTP server
#         server = smtplib.SMTP('smtp.gmail.com', 587)
#         server.starttls()
#         server.login(SENDER_EMAIL, SENDER_PASSWORD)
#         server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
#         server.quit()
#         return True
#     except Exception as e:
#         print(f"Error sending email: {e}")
#         return False
    


# # ---------------- 2. AUTHENTICATION & OTP ENDPOINTS ---------------- #

# import random
# import bcrypt
# from flask import Flask, request, jsonify

# # Single unified dictionary for storing OTPs
# otp_store = {}

# @app.route('/api/auth/send-otp', methods=['POST'])
# def request_otp():
#     data = request.json or {}
#     email = str(data.get('email', '')).strip().lower()

#     if not email:
#         return jsonify({"status": "error", "message": "Email address is required"}), 400

#     otp_code = str(random.randint(100000, 999999))
#     otp_store[email] = otp_code
#     print(f"[DEBUG STORE] Email: '{email}' | OTP: '{otp_code}'")

#     email_sent = send_otp_email(email, otp_code)

#     if email_sent:
#         return jsonify({"status": "success", "message": f"OTP sent to {email}"})
#     else:
#         return jsonify({"status": "error", "message": "Failed to send email via SMTP"}), 500


# @app.route('/api/auth/verify-otp', methods=['POST'])
# def verify_otp():
#     data = request.json or {}
#     email = str(data.get('email', '')).strip().lower()
#     user_otp = str(data.get('otp', '')).strip()

#     stored_otp = otp_store.get(email)
#     print(f"[DEBUG VERIFY] Email: '{email}' | Stored: '{stored_otp}' | Received: '{user_otp}'")

#     if stored_otp and stored_otp == user_otp:
#         return jsonify({"status": "success", "message": "OTP verified successfully!"})
#     else:
#         return jsonify({"status": "error", "message": "Invalid or expired OTP code!"}), 400


# @app.route('/api/verify-and-register', methods=['POST'])
# def verify_and_register():
#     data = request.json or {}
#     name = str(data.get('full_name', '')).strip()
#     email = str(data.get('email', '')).strip().lower()
#     password = str(data.get('password', '')).encode('utf-8')
#     pin = str(data.get('pin', '')).encode('utf-8')
#     user_otp = str(data.get('otp', '')).strip()

#     print(f"[DEBUG REGISTER] Email: '{email}' | User OTP: '{user_otp}' | Stored OTP: '{otp_store.get(email)}'")

#     # Validate OTP Code against unified otp_store
#     if email not in otp_store or otp_store[email] != user_otp:
#         return jsonify({"status": "error", "message": "Invalid or expired OTP code!"}), 400

#     hashed_pw = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
#     hashed_pin = bcrypt.hashpw(pin, bcrypt.gensalt()).decode('utf-8')

#     db = get_db()
#     cursor = db.cursor(dictionary=True, buffered=True)

#     try:
#         # Insert user into database
#         cursor.execute(
#             "INSERT INTO users (full_name, email, password_hash, pin_hash, role) VALUES (%s, %s, %s, %s, 'USER')",
#             (name, email, hashed_pw, hashed_pin)
#         )
#         user_id = cursor.lastrowid
#         account_num = f"1000{user_id:06d}"

#         # Create initial Checking Account with $1,000 balance
#         cursor.execute(
#             "INSERT INTO accounts (user_id, account_number, account_type, balance) VALUES (%s, %s, 'CHECKING', 1000.00)",
#             (user_id, account_num)
#         )
#         db.commit()

#         # Remove used OTP after successful registration
#         if email in otp_store:
#             del otp_store[email]

#         return jsonify({"status": "success", "message": "SmartBank Account Created Successfully!"}), 201
#     except Exception as e:
#         db.rollback()
#         print(f"Database Error: {e}")
#         return jsonify({"status": "error", "message": "Email already registered or database error."}), 400
#     finally:
#         cursor.close()
#         db.close()
        
        
        
        
# # In-memory temporary store for active OTP codes
# # otp_storage = {}
# # @app.route('/api/send-otp', methods=['POST'])
# # def send_otp():
# #     data = request.json or {}
# #     email = data.get('email')

# #     if not email:
# #         return jsonify({"status": "error", "message": "Email is required"}), 400

# #     # Generate a random 6-digit OTP code
# #     generated_otp = str(random.randint(100000, 999999))
# #     otp_storage[email] = generated_otp

# #     # Printed to VS Code console for testing
# #     print(f"\n==========================================")
# #     print(f"📩 OTP for {email}: [ {generated_otp} ]")
# #     print(f"==========================================\n")

# #     return jsonify({
# #         "status": "success", 
# #         "message": f"OTP sent to {email}. Check your Flask backend console for the 6-digit code!"
# #     }), 200


# ---------------- 3. USER TRANSACTION ENDPOINTS ---------------- #

@app.route('/api/transfer', methods=['POST'])
def transfer_money():
    data = request.json or {}
    sender_account_id = data.get('sender_account_id')
    receiver_account_number = str(data.get('receiver_account_number', '')).strip()
    entered_pin = str(data.get('pin', '')).strip()

    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        amount = 0.0

    if not sender_account_id or not receiver_account_number or amount <= 0 or not entered_pin:
        return jsonify({"status": "error", "message": "Invalid transfer parameters"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # 1. Fetch Sender details & PIN
        cursor.execute("""
            SELECT a.account_id, a.account_number, a.balance, u.pin, u.email, u.full_name
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.account_id = %s
        """, (sender_account_id,))
        sender = cursor.fetchone()

        if not sender:
            return jsonify({"status": "error", "message": "Sender account not found"}), 404

        # 2. Check PIN
        stored_pin = str(sender.get('pin', '')).strip()
        pin_ok = False
        if stored_pin.startswith('$2b$') or stored_pin.startswith('$2a$'):
            pin_ok = bcrypt.checkpw(entered_pin.encode('utf-8'), stored_pin.encode('utf-8'))
        else:
            pin_ok = (stored_pin == entered_pin)

        if not pin_ok:
            return jsonify({"status": "error", "message": "Invalid 4-digit PIN"}), 401

        # 3. Check Balance
        if float(sender['balance']) < amount:
            return jsonify({"status": "error", "message": "Insufficient balance"}), 400

        # 4. Fetch Receiver details
        cursor.execute("""
            SELECT a.account_id, a.account_number, a.balance, u.email, u.full_name
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.account_number = %s
        """, (receiver_account_number,))
        receiver = cursor.fetchone()

        if not receiver:
            return jsonify({"status": "error", "message": "Receiver account not found"}), 404

        if receiver['account_id'] == sender['account_id']:
            return jsonify({"status": "error", "message": "Cannot transfer to same account"}), 400

        # 5. Execute Balance Updates
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, sender['account_id']))
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (amount, receiver['account_id']))

        # 6. Insert Record into transactions
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        desc = f"Transfer to {receiver['full_name']} ({receiver['account_number']})"
        cursor.execute("""
            INSERT INTO transactions (account_id, transaction_type, sender_account_id, receiver_account_id, amount, category, description, created_at)
            VALUES (%s, 'DEBIT', %s, %s, %s, 'Transfer', %s, %s)
        """, (sender['account_id'], sender['account_id'], receiver['account_id'], amount, desc, now_str))

        db.commit()

        # 7. Recalculate balances for email
        sender_new_balance = float(sender['balance']) - amount
        receiver_new_balance = float(receiver['balance']) + amount

        # 8. Send Debit Email to Sender
        send_transaction_email_async(
            to_email=sender['email'],
            user_name=sender['full_name'],
            amount=amount,
            current_balance=sender_new_balance,
            tx_type_desc=f"Transfer to {receiver['full_name']} ({receiver['account_number']})",
            account_number=sender['account_number'],
            is_credit=False
        )

        # 9. Send Credit Email to Receiver
        send_transaction_email_async(
            to_email=receiver['email'],
            user_name=receiver['full_name'],
            amount=amount,
            current_balance=receiver_new_balance,
            tx_type_desc=f"Money Received from {sender['full_name']} ({sender['account_number']})",
            account_number=receiver['account_number'],
            is_credit=True
        )

        return jsonify({"status": "success", "message": f"Transferred ${amount:.2f} successfully!"}), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()
            
                                    
@app.route('/api/open-savings', methods=['POST'])
def open_savings():
    data = request.json or {}
    user_id = data.get('user_id')
    
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        account_num = f"2000{user_id:06d}"
        cursor.execute(
            "INSERT INTO accounts (user_id, account_number, account_type, balance) VALUES (%s, %s, 'SAVINGS', 100.00)",
            (user_id, account_num)
        )
        db.commit()
        return jsonify({"status": "success", "message": "High-Yield Savings Account Activated!"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        cursor.close()
        db.close()


# ---------------- 4. ADMIN MANAGEMENT ENDPOINTS ---------------- #

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.email, a.account_number, a.balance, a.is_active 
        FROM users u 
        LEFT JOIN accounts a ON u.user_id = a.user_id 
        WHERE u.role = 'USER'
    """)
    users = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"users": users}), 200

# ---------------- ADMIN: GET PENDING KYC APPLICATIONS ---------------- #

@app.route('/api/admin/pending-applications', methods=['GET'])
def get_pending_applications():
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.email, u.salary, u.photo_url, u.pan_url, u.aadhar_url,
                   a.account_id, a.account_number, a.status, a.created_at
            FROM users u
            JOIN accounts a ON u.user_id = a.user_id
            WHERE a.status = 'PENDING'
            ORDER BY a.created_at DESC
        """)
        applications = cursor.fetchall()
        return jsonify({"status": "success", "applications": applications}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()


# ---------------- ADMIN: APPROVE APPLICATION ---------------- #

@app.route('/api/admin/approve-application', methods=['POST'])
def approve_application():
    data = request.json or {}
    account_id = data.get('account_id')
    initial_deposit = float(data.get('initial_deposit', 1000.00))

    if not account_id:
        return jsonify({"status": "error", "message": "Account ID is required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            UPDATE accounts 
            SET status = 'APPROVED', is_active = 1, balance = %s 
            WHERE account_id = %s
        """, (initial_deposit, account_id))
        db.commit()

        return jsonify({"status": "success", "message": "Savings account approved and activated successfully!"}), 200
    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@app.route('/api/admin/toggle-status', methods=['POST'])
def toggle_status():
    data = request.json or {}
    account_num = data.get('account_number')
    new_status = data.get('is_active')

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("UPDATE accounts SET is_active = %s WHERE account_number = %s", (new_status, account_num))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"status": "success", "message": "Account Status Updated!"}), 200

@app.route('/api/transactions/<int:account_id>', methods=['GET'])
def get_transaction_history(account_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        # Robust query checking sender, receiver, and fallback without assuming t.account_id exists
        cursor.execute("""
            SELECT 
                t.transaction_id,
                t.sender_account_id,
                t.receiver_account_id,
                t.amount,
                t.description,
                t.created_at,
                s.account_number AS sender_acc,
                r.account_number AS receiver_acc
            FROM transactions t
            LEFT JOIN accounts s ON t.sender_account_id = s.account_id
            LEFT JOIN accounts r ON t.receiver_account_id = r.account_id
            WHERE t.sender_account_id = %s 
               OR t.receiver_account_id = %s
            ORDER BY t.created_at DESC
        """, (account_id, account_id))
        
        raw_transactions = cursor.fetchall()
        formatted_transactions = []

        for tx in raw_transactions:
            amount = float(tx.get('amount') or 0.0)
            sender_id = tx.get('sender_account_id')
            receiver_id = tx.get('receiver_account_id')
            desc = (tx.get('description') or '').strip()

            # Credit check: incoming transfer or admin deposit (sender is NULL)
            if sender_id is None or (receiver_id == account_id and sender_id != account_id):
                is_credit = True
                sign = "+"
                if desc:
                    display_title = desc
                elif sender_id is None:
                    display_title = "Admin Deposit"
                else:
                    display_title = f"Received from {tx.get('sender_acc', 'External')}"
            else:
                is_credit = False
                sign = "-"
                if desc:
                    display_title = desc
                else:
                    display_title = f"Sent to {tx.get('receiver_acc', 'External')}"

            formatted_transactions.append({
                "transaction_id": tx['transaction_id'],
                "title": display_title,
                "amount": f"{sign}${amount:.2f}",
                "is_credit": is_credit,
                "date": str(tx.get('created_at') or '')
            })

        # Return both keys for universal compatibility
        return jsonify({
            "status": "success",
            "transactions": formatted_transactions
        }), 200

    except Exception as e:
        print(f"[TRANSACTION HISTORY ERROR]: {e}")
        return jsonify({"status": "error", "message": str(e), "transactions": []}), 500

    finally:
        cursor.close()
        db.close()
        
@app.route('/statement/<int:account_id>', methods=['GET'])
def download_statement(account_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        # 1. Account Info
        cursor.execute("""
            SELECT a.account_number, a.balance, u.full_name 
            FROM accounts a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.account_id = %s
        """, (account_id,))
        account_info = cursor.fetchone()

        if not account_info:
            return "Account not found", 404

        # 2. Unified Transactions Query (No dual-table loop duplicates)
        cursor.execute("""
            SELECT 
                t.transaction_id,
                t.transaction_type,
                t.sender_account_id,
                t.receiver_account_id,
                t.amount,
                t.description,
                t.created_at,
                s_u.full_name AS sender_name,
                s.account_number AS sender_acc,
                r_u.full_name AS receiver_name,
                r.account_number AS receiver_acc
            FROM transactions t
            LEFT JOIN accounts s ON t.sender_account_id = s.account_id
            LEFT JOIN users s_u ON s.user_id = s_u.user_id
            LEFT JOIN accounts r ON t.receiver_account_id = r.account_id
            LEFT JOIN users r_u ON r.user_id = r_u.user_id
            WHERE t.sender_account_id = %s OR t.receiver_account_id = %s
            ORDER BY t.created_at DESC
        """, (account_id, account_id))
        transactions = cursor.fetchall()

        all_records = []

        for t in transactions:
            amt = float(t['amount'] or 0.0)
            s_id = t['sender_account_id']
            r_id = t['receiver_account_id']
            tx_type = str(t.get('transaction_type') or '').upper()
            desc = (t.get('description') or '').strip()

            # 1. Credit (Admin deposit or received transfer)
            if tx_type == 'CREDIT' or s_id is None or (r_id == account_id and s_id != account_id):
                display_type = "CREDIT (+)"
                amount_str = f"+${amt:.2f}"
                if desc:
                    party = desc
                elif s_id is None:
                    party = "Admin / Cash Deposit"
                else:
                    send_name = t.get('sender_name') or 'External User'
                    send_acc = t.get('sender_acc') or 'N/A'
                    party = f"{send_name} ({send_acc})"

            # 2. Debit (Transfer, Card purchase, Utility bill)
            else:
                display_type = "DEBIT (-)"
                amount_str = f"-${amt:.2f}"
                if desc:
                    party = desc
                else:
                    recv_name = t.get('receiver_name') or 'External'
                    recv_acc = t.get('receiver_acc') or 'N/A'
                    party = f"{recv_name} ({recv_acc})"

            all_records.append({
                "date": t['created_at'],
                "type": display_type,
                "party": party,
                "amount": amount_str
            })

        # 3. Build PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        import io, time

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("<b>SmartBank Account Statement</b>", styles['Title']))
        elements.append(Spacer(1, 12))

        info_text = f"""
        <b>Account Holder:</b> {account_info['full_name']}<br/>
        <b>Account Number:</b> {account_info['account_number']}<br/>
        <b>Current Balance:</b> ${float(account_info['balance']):.2f}
        """
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 16))

        table_data = [["Date & Time", "Type", "Opposite Party (Name & Acc No)", "Amount"]]

        for rec in all_records:
            date_str = str(rec['date'])[:19]
            table_data.append([date_str, rec['type'], rec['party'], rec['amount']])

        t = Table(table_data, colWidths=[110, 70, 230, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(t)
        doc.build(elements)

        buffer.seek(0)
        from flask import make_response
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=statement_{account_info["account_number"]}_{int(time.time())}.pdf'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    except Exception as e:
        print(f"[STATEMENT ERROR]: {e}")
        return f"Error generating PDF statement: {e}", 500

    finally:
        cursor.close()
        db.close()
                        
#-------------------------------------------------------------------------------------       

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/api/savings/apply', methods=['POST'])
def apply_savings():
    user_id = request.form.get('user_id')
    income = request.form.get('income_details')
    aadhar = request.form.get('aadhar_number')
    pan = request.form.get('pan_number')

    if not all([user_id, income, aadhar, pan]):
        return jsonify({"status": "error", "message": "All text fields are required"}), 400

    # Save uploaded files
    photo = request.files.get('user_photo')
    aadhar_img = request.files.get('aadhar_photo')
    pan_img = request.files.get('pan_photo')

    photo_path = None
    aadhar_photo_path = None
    pan_photo_path = None

    if photo:
        photo_name = secure_filename(f"user_{user_id}_photo_{photo.filename}")
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_name)
        photo.save(photo_path)

    if aadhar_img:
        aadhar_name = secure_filename(f"user_{user_id}_aadhar_{aadhar_img.filename}")
        aadhar_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], aadhar_name)
        aadhar_img.save(aadhar_photo_path)

    if pan_img:
        pan_name = secure_filename(f"user_{user_id}_pan_{pan_img.filename}")
        pan_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], pan_name)
        pan_img.save(pan_photo_path)

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        cursor.execute("SELECT status FROM savings_applications WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()
        if existing:
            return jsonify({"status": "error", "message": f"Application already submitted. Status: {existing['status']}"}), 400

        cursor.execute("""
            INSERT INTO savings_applications 
            (user_id, income_details, aadhar_number, pan_number, photo_path, aadhar_photo_path, pan_photo_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, income, aadhar, pan, photo_path, aadhar_photo_path, pan_photo_path))
        db.commit()

        return jsonify({"status": "success", "message": "Savings account application submitted with photos!"})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()

# 3. Admin Approves & Opens Savings Account

@app.route('/api/admin/savings/approve', methods=['POST'])
def approve_savings():
    data = request.json
    application_id = data.get('application_id')
    user_id = data.get('user_id')

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        # Generate new 10-digit savings account number starting with '20'
        new_acc_num = f"20{random.randint(10000000, 99999999)}"

        # 1. Create Savings Account with $0.00 initial balance
        cursor.execute("""
            INSERT INTO accounts (user_id, account_number, account_type, balance, is_active)
            VALUES (%s, %s, 'SAVINGS', 0.00, 1)
        """, (user_id, new_acc_num))

        # 2. Update Application Status to APPROVED
        cursor.execute("""
            UPDATE savings_applications SET status = 'APPROVED' WHERE application_id = %s
        """, (application_id,))

        db.commit()
        return jsonify({
            "status": "success", 
            "message": f"Savings Account {new_acc_num} approved successfully!"
        })
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()
        
# Fetch all accounts (Checking & Savings) with full user info
@app.route('/api/admin/all-accounts', methods=['GET'])
def admin_get_all_accounts():
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT a.account_id, a.user_id, a.account_number, a.account_type, 
                   a.balance, a.is_active, COALESCE(a.status, 'APPROVED') AS status,
                   u.full_name, u.email
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            ORDER BY a.account_id DESC
        """)
        accounts = cursor.fetchall()
        return jsonify({"status": "success", "accounts": accounts}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()
        
# Freeze or Unfreeze a specific account
@app.route('/api/admin/toggle-account-freeze', methods=['POST'])
def toggle_account_freeze():
    data = request.json
    account_id = data.get('account_id')
    is_active = data.get('is_active')  # 1 for active, 0 for frozen

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        cursor.execute("""
            UPDATE accounts SET is_active = %s WHERE account_id = %s
        """, (is_active, account_id))
        db.commit()

        status_str = "activated" if is_active == 1 else "frozen"
        return jsonify({"status": "success", "message": f"Account status successfully updated to {status_str}."})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()                
        
@app.route('/api/admin/delete-account', methods=['POST'])
def admin_delete_account():
    data = request.json or {}
    account_id = data.get('account_id')

    if not account_id:
        return jsonify({"status": "error", "message": "Account ID is required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # 1. Find user_id associated with this account
        cursor.execute("SELECT user_id, email FROM accounts JOIN users USING(user_id) WHERE account_id = %s", (account_id,))
        record = cursor.fetchone()

        if not record:
            # Check if account exists without join
            cursor.execute("SELECT user_id FROM accounts WHERE account_id = %s", (account_id,))
            acc_record = cursor.fetchone()
            user_id = acc_record['user_id'] if acc_record else None
        else:
            user_id = record['user_id']

        # 2. Clean up foreign-key dependencies
        cursor.execute("DELETE FROM transactions WHERE sender_account_id = %s OR receiver_account_id = %s", (account_id, account_id))
        cursor.execute("DELETE FROM fixed_deposits WHERE account_id = %s", (account_id,))
        cursor.execute("DELETE FROM virtual_cards WHERE account_id = %s", (account_id,))
        cursor.execute("DELETE FROM bill_payments WHERE account_id = %s", (account_id,))

        # 3. Delete from accounts table
        cursor.execute("DELETE FROM accounts WHERE account_id = %s", (account_id,))

        # 4. Delete user profile completely if no other accounts exist
        if user_id:
            cursor.execute("SELECT COUNT(*) AS remaining_accs FROM accounts WHERE user_id = %s", (user_id,))
            counts = cursor.fetchone()
            if counts['remaining_accs'] == 0:
                cursor.execute("DELETE FROM beneficiaries WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

        db.commit()
        return jsonify({"status": "success", "message": "Account and associated user data deleted completely."}), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()
        
#-----------------------------------NEW Features----------------------------------------

@app.route('/api/analytics/<int:account_id>', methods=['GET'])
def get_account_analytics(account_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # 1. Total Expense
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0) AS total_expense
            FROM transactions
            WHERE sender_account_id = %s
        """, (account_id,))
        exp_row = cursor.fetchone()
        total_expense = float(exp_row['total_expense']) if exp_row and exp_row['total_expense'] else 0.0

        # 2. Total Income (exclude transfers to self)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.0) AS total_income
            FROM transactions
            WHERE receiver_account_id = %s 
              AND (sender_account_id IS NULL OR sender_account_id != %s)
        """, (account_id, account_id))
        inc_row = cursor.fetchone()
        total_income = float(inc_row['total_income']) if inc_row and inc_row['total_income'] else 0.0

        # 3. Category Breakdown
        cursor.execute("""
            SELECT 
                COALESCE(category, 'General') AS category_name,
                COALESCE(SUM(amount), 0.0) AS total_amount
            FROM transactions
            WHERE sender_account_id = %s
            GROUP BY COALESCE(category, 'General')
        """, (account_id,))
        categories = cursor.fetchall()
        for cat in categories:
            cat['total_amount'] = float(cat['total_amount'])

        # 4. Daily Spending (Last 7 Days) for charts
        cursor.execute("""
            SELECT DATE(created_at) AS date_str, COALESCE(SUM(amount), 0.0) AS day_total
            FROM transactions
            WHERE sender_account_id = %s
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) DESC
            LIMIT 7
        """, (account_id,))
        daily_rows = cursor.fetchall()
        daily_spending = [
            {"date": str(r['date_str']), "amount": float(r['day_total'])} 
            for r in daily_rows
        ]

        return jsonify({
            "status": "success",
            "total_income": total_income,
            "total_expense": total_expense,
            "categories": categories,
            "daily_spending": daily_spending
        }), 200

    except Exception as e:
        print(f"[ANALYTICS ERROR]: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "total_income": 0.0,
            "total_expense": 0.0,
            "categories": [],
            "daily_spending": []
        }), 500
    finally:
        cursor.close()
        db.close()
        
# 1. Add a New Beneficiary
@app.route('/api/beneficiaries/add', methods=['POST'])
def add_beneficiary():
    data = request.json
    user_id = data.get('user_id')
    nickname = data.get('nickname')
    account_number = data.get('account_number')

    if not all([user_id, nickname, account_number]):
        return jsonify({"status": "error", "message": "Nickname and Account Number are required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        # Check if beneficiary account number exists in banking system
        cursor.execute("SELECT account_id FROM accounts WHERE account_number = %s", (account_number,))
        target_account = cursor.fetchone()
        if not target_account:
            return jsonify({"status": "error", "message": "Account number does not exist in SmartBank"}), 404

        cursor.execute("""
            INSERT INTO beneficiaries (user_id, nickname, account_number)
            VALUES (%s, %s, %s)
        """, (user_id, nickname, account_number))
        db.commit()

        return jsonify({"status": "success", "message": f"Saved {nickname} to your beneficiaries!"})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()

# 2. Get All Saved Beneficiaries for User
@app.route('/api/beneficiaries/<int:user_id>', methods=['GET'])
def get_beneficiaries(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        cursor.execute("""
            SELECT beneficiary_id, nickname, account_number, created_at 
            FROM beneficiaries 
            WHERE user_id = %s
            ORDER BY nickname ASC
        """, (user_id,))
        beneficiaries = cursor.fetchall()
        return jsonify({"status": "success", "beneficiaries": beneficiaries})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()
        
# Change Transaction PIN Endpoint
@app.route('/api/user/change-pin', methods=['POST'])
def change_pin():
    data = request.json or {}
    user_id = data.get('user_id')
    old_pin = str(data.get('old_pin', '')).encode('utf-8')
    new_pin = str(data.get('new_pin', '')).encode('utf-8')

    if not user_id or not old_pin or not new_pin:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if len(data.get('new_pin', '')) != 4:
        return jsonify({"status": "error", "message": "PIN must be exactly 4 digits"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        # 1. Fetch existing PIN using 'pin' and 'user_id'
        cursor.execute("SELECT pin FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        stored_pin = user.get('pin', '')

        # 2. Verify current PIN (supports both hashed and plaintext stored PINs)
        pin_matched = False
        if stored_pin and (stored_pin.startswith('$2b$') or stored_pin.startswith('$2a$')):
            pin_matched = bcrypt.checkpw(old_pin, stored_pin.encode('utf-8'))
        else:
            pin_matched = (stored_pin == data.get('old_pin'))

        if not pin_matched:
            return jsonify({"status": "error", "message": "Incorrect current PIN"}), 400

        # 3. Hash the new PIN
        new_pin_hash = bcrypt.hashpw(new_pin, bcrypt.gensalt()).decode('utf-8')

        # 4. Update 'pin' column using 'user_id'
        cursor.execute("UPDATE users SET pin = %s WHERE user_id = %s", (new_pin_hash, user_id))
        db.commit()

        return jsonify({"status": "success", "message": "Transaction PIN updated successfully!"}), 200

    except Exception as e:
        db.rollback()
        print(f"[CHANGE PIN ERROR]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        db.close()

# Fetch updated user profile and primary checking/savings accounts
@app.route('/api/user/dashboard-data/<int:user_id>', methods=['GET'])
def get_user_dashboard_data(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:
        # Fetch user
        cursor.execute("SELECT user_id, full_name, email, role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Fetch accounts
        cursor.execute("""
            SELECT account_id, account_number, account_type, balance, is_active 
            FROM accounts 
            WHERE user_id = %s 
            ORDER BY account_id ASC
        """, (user_id,))
        accounts = cursor.fetchall()

        return jsonify({
            "status": "success",
            "user": user,
            "accounts": accounts
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/utility/pay-bill', methods=['POST'])
def pay_utility_bill():
    data = request.json or {}
    user_id = data.get('user_id')
    account_id = data.get('account_id')
    biller_type = str(data.get('biller_type', '')).upper()
    biller_name = str(data.get('biller_name', '')).strip()
    consumer_number = str(data.get('consumer_number', '')).strip()
    entered_pin = str(data.get('pin', '')).strip()

    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        amount = 0.0

    if not user_id or not account_id or not biller_type or not consumer_number or amount <= 0 or not entered_pin:
        return jsonify({"status": "error", "message": "Invalid utility payment payload"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT a.account_id, a.account_number, a.balance, u.pin, u.email, u.full_name 
            FROM accounts a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.account_id = %s AND u.user_id = %s
        """, (account_id, user_id))
        user_account = cursor.fetchone()

        if not user_account:
            return jsonify({"status": "error", "message": "Account not found"}), 404

        stored_pin = str(user_account.get('pin', '')).strip()
        pin_matched = False
        if stored_pin.startswith('$2b$') or stored_pin.startswith('$2a$'):
            pin_matched = bcrypt.checkpw(entered_pin.encode('utf-8'), stored_pin.encode('utf-8'))
        else:
            pin_matched = (stored_pin == entered_pin)

        if not pin_matched:
            return jsonify({"status": "error", "message": "Invalid transaction PIN"}), 401

        if float(user_account['balance']) < amount:
            return jsonify({"status": "error", "message": "Insufficient balance"}), 400

        # Deduct Funds
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, account_id))

        category_name = biller_type.replace('_', ' ').title()
        description_text = f"{biller_name} ({category_name.upper()})"

        # Insert Transaction
        cursor.execute("""
            INSERT INTO transactions (account_id, transaction_type, sender_account_id, receiver_account_id, amount, category, description)
            VALUES (%s, 'DEBIT', %s, NULL, %s, %s, %s)
        """, (account_id, account_id, amount, category_name, description_text))

        # Insert Bill Payment Record
        cursor.execute("""
            INSERT INTO bill_payments (user_id, account_id, biller_name, biller_type, consumer_number, amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'SUCCESS')
        """, (user_id, account_id, biller_name, biller_type, consumer_number, amount))

        db.commit()

        # Send Debit Email
        new_balance = float(user_account['balance']) - amount
        send_transaction_email_async(
            to_email=user_account['email'],
            user_name=user_account['full_name'],
            amount=amount,
            current_balance=new_balance,
            tx_type_desc=f"{category_name}: {biller_name} ({consumer_number})",
            account_number=user_account['account_number'],
            is_credit=False
        )

        return jsonify({"status": "success", "message": f"{category_name} payment completed!"}), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()
                                     
@app.route('/api/admin/deposit', methods=['POST'])
def admin_deposit_funds():
    data = request.json or {}
    account_number = str(data.get('account_number', '')).strip()

    try:
        amount = float(data.get('amount', 0.0))
    except (ValueError, TypeError):
        amount = 0.0

    if not account_number or amount <= 0:
        return jsonify({"status": "error", "message": "Invalid account or amount"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT a.account_id, a.account_number, a.balance, u.email, u.full_name
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.account_number = %s
        """, (account_number,))
        target_account = cursor.fetchone()

        if not target_account:
            return jsonify({"status": "error", "message": "Account not found"}), 404

        target_acc_id = target_account['account_id']
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Add funds
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (amount, target_acc_id))

        # Record Credit Transaction
        cursor.execute("""
            INSERT INTO transactions (account_id, transaction_type, sender_account_id, receiver_account_id, amount, category, description, created_at)
            VALUES (%s, 'CREDIT', NULL, %s, %s, 'Deposit', 'Admin Cash Deposit', %s)
        """, (target_acc_id, target_acc_id, amount, now_str))

        db.commit()

        # Send Credit Email
        new_balance = float(target_account['balance']) + amount
        send_transaction_email_async(
            to_email=target_account['email'],
            user_name=target_account['full_name'],
            amount=amount,
            current_balance=new_balance,
            tx_type_desc="Admin Cash Deposit / Top-up",
            account_number=target_account['account_number'],
            is_credit=True
        )

        return jsonify({"status": "success", "message": f"Successfully deposited ${amount:.2f}"}), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()        

# ==========================================
# 1. FIXED DEPOSITS (FD) WITH DATETIME
# ==========================================

from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
from flask import Flask, request, jsonify


def get_interest_rate_for_tenure(months):
    """
    Dynamic Tiered Annual Interest Rate:
    - 3 to 5 Months: 5.0%
    - 6 to 11 Months: 6.0%
    - 12 to 23 Months (1 - <2 Yrs): 7.0%
    - 24 to 35 Months (2 - <3 Yrs): 7.5%
    - 36 to 60 Months (3 - 5 Yrs): 8.0%
    """
    if months < 6:
        return 5.00
    elif months < 12:
        return 6.00
    elif months < 24:
        return 7.00
    elif months < 36:
        return 7.50
    else:
        return 8.00

@app.route('/api/fd/create', methods=['POST'])
def create_fixed_deposit():
    data = request.json or {}
    account_id = data.get('account_id')
    amount = float(data.get('amount', 0))
    tenure_months = int(data.get('tenure_months', 12))

    if not account_id or amount <= 0 or tenure_months < 1:
        return jsonify({"status": "error", "message": "Invalid FD amount or tenure"}), 400

    interest_rate = get_interest_rate_for_tenure(tenure_months)

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # Check current balance
        cursor.execute("SELECT balance, account_number FROM accounts WHERE account_id = %s", (account_id,))
        acc = cursor.fetchone()
        if not acc:
            return jsonify({"status": "error", "message": "Account not found"}), 404

        if float(acc['balance']) < amount:
            return jsonify({"status": "error", "message": "Insufficient account balance"}), 400

        # Calculate projected full maturity (Simple Annual Interest)
        interest_earned = amount * (interest_rate / 100.0) * (tenure_months / 12.0)
        maturity_amount = round(amount + interest_earned, 2)

        # Deduct amount from account
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, account_id))

        # Insert record into fixed_deposits
        cursor.execute("""
            INSERT INTO fixed_deposits 
            (account_id, principal_amount, tenure_months, interest_rate, maturity_amount, status)
            VALUES (%s, %s, %s, %s, %s, 'ACTIVE')
        """, (account_id, amount, tenure_months, interest_rate, maturity_amount))

        # Log transaction
        # Check how your transactions table is structured. 
        # If your transactions table uses account_id:
        cursor.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount, description)
            VALUES (%s, 'DEBIT', %s, %s)
        """, (account_id, amount, f"Fixed Deposit #{tenure_months}M @ {interest_rate}%"))

        db.commit()
        return jsonify({
            "status": "success",
            "message": f"FD of ${amount:,.2f} booked successfully for {tenure_months} months at {interest_rate}% p.a.!"
        }), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/fd/<int:account_id>', methods=['GET'])
def get_fixed_deposits(account_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT fd_id, account_id, principal_amount, tenure_months, 
                   interest_rate, maturity_amount, status, payout_amount,
                   DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') as created_at,
                   DATE_FORMAT(closed_at, '%Y-%m-%d %H:%i') as closed_at
            FROM fixed_deposits 
            WHERE account_id = %s 
            ORDER BY fd_id DESC
        """, (account_id,))
        fds = cursor.fetchall()
        return jsonify({"status": "success", "fixed_deposits": fds}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/fd/cancel', methods=['POST'])
def cancel_fixed_deposit():
    """Premature cancellation: computes accrued interest according to actual days held."""
    data = request.json or {}
    fd_id = data.get('fd_id')
    account_id = data.get('account_id')

    if not fd_id or not account_id:
        return jsonify({"status": "error", "message": "FD ID and Account ID are required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT * FROM fixed_deposits WHERE fd_id = %s AND account_id = %s", (fd_id, account_id))
        fd = cursor.fetchone()

        if not fd:
            return jsonify({"status": "error", "message": "Fixed deposit not found"}), 404
        if fd['status'] != 'ACTIVE':
            return jsonify({"status": "error", "message": "FD is already closed or cancelled"}), 400

        principal = float(fd['principal_amount'])
        created_at = fd['created_at']
        now = datetime.now()

        # Calculate exact elapsed days (minimum 1 day for calculation)
        days_held = max(1, (now - created_at).days)
        years_held = days_held / 365.0

        # Applicable interest rate based on time held
        months_held = int(days_held // 30)
        applicable_rate = get_interest_rate_for_tenure(months_held)

        # Accrued interest calculated on actual period
        accrued_interest = principal * (applicable_rate / 100.0) * years_held
        total_payout = round(principal + accrued_interest, 2)

        # Credit funds back to user account
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (total_payout, account_id))

        # Mark FD as CLOSED with payout details
        cursor.execute("""
            UPDATE fixed_deposits 
            SET status = 'CLOSED', payout_amount = %s, closed_at = NOW() 
            WHERE fd_id = %s
        """, (total_payout, fd_id))

        # Log credit transaction
        cursor.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount, description)
            VALUES (%s, 'CREDIT', %s, %s)
        """, (account_id, total_payout, f"FD #{fd_id} Closed (Principal: ${principal:.2f}, Interest: ${accrued_interest:.2f})"))

        db.commit()
        return jsonify({
            "status": "success",
            "message": f"FD #{fd_id} closed! ${total_payout:,.2f} (Principal: ${principal:,.2f} + Interest: ${accrued_interest:,.2f}) credited to your account.",
            "payout": total_payout,
            "interest_earned": round(accrued_interest, 2),
            "days_held": days_held
        }), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()
        
# ==========================================
# 2. VIRTUAL DEBIT CARD WITH DYNAMIC EXPIRY
# ==========================================

@app.route('/api/card/<int:account_id>', methods=['GET'])
def get_virtual_card(account_id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT * FROM virtual_cards WHERE account_id = %s", (account_id,))
        card = cursor.fetchone()

        if not card:
            card_num = "4" + "".join([str(random.randint(0, 9)) for _ in range(15)])
            cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
            expiry_date = "12/29"

            cursor.execute("""
                INSERT INTO virtual_cards (account_id, card_number, cvv, expiry_date, is_frozen)
                VALUES (%s, %s, %s, %s, 0)
            """, (account_id, card_num, cvv, expiry_date))
            db.commit()

            cursor.execute("SELECT * FROM virtual_cards WHERE account_id = %s", (account_id,))
            card = cursor.fetchone()

        # Calculate today's real spent total for this account
        today_start = datetime.now().strftime('%Y-%m-%d 00:00:00')
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0.00) AS total_today 
            FROM transactions 
            WHERE sender_account_id = %s AND created_at >= %s
        """, (account_id, today_start))
        row = cursor.fetchone()
        today_spent = float(row['total_today']) if row else 0.0

        return jsonify({
            "status": "success", 
            "card": card, 
            "spent_today": today_spent
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/card/toggle-freeze', methods=['POST'])
def toggle_card_freeze():
    data = request.json or {}
    account_id = data.get('account_id')

    if not account_id:
        return jsonify({"status": "error", "message": "Account ID required"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT is_frozen FROM virtual_cards WHERE account_id = %s", (account_id,))
        card = cursor.fetchone()

        if not card:
            return jsonify({"status": "error", "message": "Virtual card not found"}), 404

        new_status = 0 if card['is_frozen'] == 1 else 1
        cursor.execute("UPDATE virtual_cards SET is_frozen = %s WHERE account_id = %s", (new_status, account_id))
        db.commit()

        msg = "Card frozen successfully" if new_status == 1 else "Card unfrozen successfully"
        return jsonify({"status": "success", "message": msg, "is_frozen": new_status}), 200
    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()


@app.route('/api/card/pay-online', methods=['POST'])
def card_online_payment():
    data = request.json or {}
    card_number = (data.get('card_number') or '').strip()
    cvv = (data.get('cvv') or '').strip()
    merchant_name = data.get('merchant_name', 'Online Store').strip()

    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        amount = 0.0

    if not card_number or not cvv or amount <= 0:
        return jsonify({"status": "error", "message": "Invalid payment details"}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT c.account_id, c.is_frozen, a.account_number, a.balance, u.email, u.full_name
            FROM virtual_cards c
            JOIN accounts a ON c.account_id = a.account_id
            JOIN users u ON a.user_id = u.user_id
            WHERE c.card_number = %s AND c.cvv = %s
        """, (card_number, cvv))
        card_data = cursor.fetchone()

        if not card_data:
            return jsonify({"status": "error", "message": "Invalid Card Number or CVV"}), 400

        if card_data['is_frozen'] == 1:
            return jsonify({"status": "error", "message": "Card is FROZEN"}), 403

        if float(card_data['balance']) < amount:
            return jsonify({"status": "error", "message": "Insufficient account balance"}), 400

        account_id = card_data['account_id']
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Deduct balance
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, account_id))

        # Insert Transaction
        desc = f"Card Purchase - {merchant_name} (VIRTUAL CARD)"
        cursor.execute("""
            INSERT INTO transactions (account_id, transaction_type, sender_account_id, receiver_account_id, amount, category, description, created_at)
            VALUES (%s, 'DEBIT', %s, NULL, %s, 'Card Purchase', %s, %s)
        """, (account_id, account_id, amount, desc, now_str))

        # Insert Bill Payment Record
        cursor.execute("""
            INSERT INTO bill_payments (account_id, biller_name, biller_type, amount)
            VALUES (%s, %s, 'VIRTUAL_CARD', %s)
        """, (account_id, f"Card Purchase - {merchant_name}", amount))

        db.commit()

        # Send Debit Email
        new_balance = float(card_data['balance']) - amount
        send_transaction_email_async(
            to_email=card_data['email'],
            user_name=card_data['full_name'],
            amount=amount,
            current_balance=new_balance,
            tx_type_desc=desc,
            account_number=card_data['account_number'],
            is_credit=False
        )

        return jsonify({
            "status": "success", 
            "message": f"Payment of ${amount:.2f} to {merchant_name} successful!"
        }), 200

    except Exception as e:
        if 'db' in locals() and db.is_connected():
            db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()
            
            
# ==========================================
# 3. QR CODE RECEIVE / SCAN VERIFICATION
# ==========================================

@app.route('/api/qr/verify/<string:account_number>', methods=['GET'])
def verify_qr_account(account_number):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("""
            SELECT a.account_id, a.account_number, u.full_name 
            FROM accounts a 
            JOIN users u ON a.user_id = u.user_id 
            WHERE a.account_number = %s
        """, (account_number.strip(),))
        account = cursor.fetchone()

        if not account:
            return jsonify({"status": "error", "message": "Invalid QR Code or Account Not Found"}), 404

        return jsonify({
            "status": "success",
            "account": {
                "account_id": account['account_id'],
                "account_number": account['account_number'],
                "receiver_name": account['full_name']
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        db.close()
        
                                
# ---------------- 5. SERVER RUNNER ---------------- #
import os

if __name__ == '__main__':
    # Determine execution environment
    ENV = os.environ.get('FLASK_ENV', 'production')

    if ENV == 'development':
        print("Starting Flask Development Server...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        # Production WSGI Server using Waitress
        from waitress import serve
        print("Starting SmartBank WSGI Production Server on http://0.0.0.0:5000...")
        serve(app, host='0.0.0.0', port=5000, threads=8)