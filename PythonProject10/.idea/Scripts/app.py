import os
import random
import datetime
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=7)
jwt = JWTManager(app)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Database Connection
def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD"),
        host=os.getenv("DATABASE_HOST"),
        port=os.getenv("DATABASE_PORT")
    )

# Helper Functions
def generate_otp():
    return str(random.randint(100000, 999999))

def generate_investor_id():
    return f"I{random.randint(1000, 9999)}"

def send_email(to_email, subject, body):
    try:
        message = Mail(
            from_email=os.getenv("SENDGRID_EMAIL"),
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Email sent to {to_email}. Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {e}")

def send_sms(phone_number, otp):
    try:
        message = twilio_client.messages.create(
            body=f"Your OTP for phone verification is: {otp}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"✅ SMS sent to {phone_number}. SID: {message.sid}")
    except Exception as e:
        print(f"❌ Error sending SMS to {phone_number}: {e}")

# API Routes
@app.route('/api/signup', methods=['POST'])
def signup_user():
    try:
        data = request.get_json()
        first_name = data['first_name']
        last_name = data['last_name']
        email = data['email']
        phone_number = data['phone_number']
        password = data['password']
        reenter_password = data['reenter_password']
        interested_in = data['interested_in']

        if password != reenter_password:
            return jsonify({"error": "Passwords do not match"}), 400

        hashed_password = generate_password_hash(password)
        email_otp = generate_otp()
        email_otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users (first_name, last_name, email, phone_number, password, email_otp, email_otp_expiry, email_verified, phone_verified, investor_id, interested_in)
        VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, FALSE, NULL, %s)
        """, (first_name, last_name, email, phone_number, hashed_password, email_otp, email_otp_expiry, interested_in))

        conn.commit()
        cursor.close()
        conn.close()

        send_email(email, "Verify Your Email - Real One Invest", f"Your OTP: {email_otp}")

        return jsonify({"message": "Signup successful. Please verify your email."}), 201
    except Exception as e:
        return jsonify({"error": f"Signup failed: {str(e)}"}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    try:
        data = request.get_json()
        email = data['email']
        email_otp = data['otp']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email_otp FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or user[0] != email_otp:
            return jsonify({"error": "Invalid OTP"}), 400

        cursor.execute("UPDATE users SET email_verified = TRUE WHERE email = %s", (email,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Email verified successfully."}), 200
    except Exception as e:
        return jsonify({"error": "Email verification failed"}), 500

@app.route('/api/send-phone-otp', methods=['POST'])
def send_phone_otp():
    try:
        data = request.get_json()
        email = data['email']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT phone_number FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        phone_number = user[0]
        phone_otp = generate_otp()
        cursor.execute("UPDATE users SET phone_otp = %s WHERE email = %s", (phone_otp, email))
        conn.commit()

        send_sms(phone_number, phone_otp)

        return jsonify({"message": "Phone OTP sent successfully."}), 200

    except Exception as e:
        return jsonify({"error": "Failed to send phone OTP"}), 500

@app.route('/api/verify-phone', methods=['POST'])
def verify_phone():
    try:
        data = request.get_json()
        email = data['email']
        phone_otp = data['otp']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT phone_otp FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or user[0] != phone_otp:
            return jsonify({"error": "Invalid OTP"}), 400

        investor_id = generate_investor_id()

        cursor.execute("UPDATE users SET phone_verified = TRUE, investor_id = %s WHERE email = %s", (investor_id, email))
        conn.commit()

        send_email(email, "Welcome to Real One Invest!", f"Thank you for signing up!\nYour Investor ID is {investor_id}. Welcome to Real One Invest!")

        return jsonify({"message": "Phone verified successfully. Welcome email sent!", "investor_id": investor_id}), 200
    except Exception as e:
        return jsonify({"error": "Phone verification failed"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
