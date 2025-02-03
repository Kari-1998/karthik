import os
import random
import datetime
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import smtplib

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "super-secret-key")
jwt = JWTManager(app)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# Database Connection
def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DATABASE_NAME", "realoneinvest"),
        user=os.getenv("DATABASE_USER", "karthik1"),
        password=os.getenv("DATABASE_PASSWORD", "Info123tech"),
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=os.getenv("DATABASE_PORT", "5433")
    )


# Ensure Users Table Exists
def create_users_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone_number VARCHAR(20) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            email_otp VARCHAR(6),
            email_otp_expiry TIMESTAMP,
            phone_otp VARCHAR(6),
            phone_otp_expiry TIMESTAMP,
            email_verified BOOLEAN DEFAULT FALSE,
            phone_verified BOOLEAN DEFAULT FALSE,
            investor_id VARCHAR(10) UNIQUE,
            interested_in VARCHAR(50)
        );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Users table checked/created successfully.")
    except Exception as e:
        print(f"❌ Error creating users table: {e}")


# Helper Functions
def generate_otp():
    return str(random.randint(100000, 999999))


def generate_investor_id():
    return f"I{random.randint(1000, 9999)}"


def send_email(to_email, subject, body):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 465  # SSL port for Gmail
        sender_email = os.getenv("EMAIL_APPCODE")  # Your Gmail email address
        password = os.getenv("APP_PASSWORD")  # Your Google App Password

        # Create the email content
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Establish a secure SSL connection with the Gmail SMTP server
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, to_email, message.as_string())

        print(f"✅ Email sent to {to_email} via Gmail SMTP.")
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
        phone_otp = generate_otp()
        otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users (first_name, last_name, email, phone_number, password, email_otp, email_otp_expiry, phone_otp, phone_otp_expiry, email_verified, phone_verified, investor_id, interested_in)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, FALSE, NULL, %s)
        """, (first_name, last_name, email, phone_number, hashed_password, email_otp, otp_expiry, phone_otp, otp_expiry,
              interested_in))

        conn.commit()
        cursor.close()
        conn.close()

        send_email(email, "Verify Your Email - Real One Invest", f"Your OTP: {email_otp}")
        send_sms(phone_number, phone_otp)

        return jsonify({"message": "Signup successful. OTPs sent for email and phone."}), 201
    except Exception as e:
        return jsonify({"error": f"Signup failed: {str(e)}"}), 500


@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    try:
        data = request.get_json()
        print(f"Request Data: {data}")  # Debugging line

        email = data['email']
        otp = data['otp']

        conn = get_connection()
        cursor = conn.cursor()

        # Fetch the stored OTP for the given email
        cursor.execute("SELECT email_otp FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found."}), 404

        stored_otp = user[0]
        print(f"Stored OTP for {email}: {stored_otp}")  # Debugging line

        # Verify if the OTP matches
        if stored_otp != otp:
            return jsonify({"error": "Invalid OTP"}), 400

        # If OTP is valid, update the email_verified field
        cursor.execute("UPDATE users SET email_verified = TRUE WHERE email = %s", (email,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Email verified successfully."}), 200

    except Exception as e:
        print(f"Error during email verification: {str(e)}")  # Log the actual error for debugging
        return jsonify({"error": "Email verification failed"}), 500


@app.route('/api/verify-phone', methods=['POST'])
def verify_phone():
    try:
        data = request.get_json()
        phone_number = data['phone_number']
        otp = data['otp']

        # Database connection
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch the stored OTP for the given phone number
        cursor.execute("SELECT phone_otp, email FROM users WHERE phone_number = %s", (phone_number,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found."}), 404

        stored_otp, email = user
        print(f"Stored OTP for {phone_number}: {stored_otp}")  # Debugging line

        # Verify if the OTP matches
        if stored_otp != otp:
            return jsonify({"error": "Invalid OTP"}), 400

        # If OTP is valid, generate investor_id and update user
        investor_id = generate_investor_id()

        # Update phone_verified and assign investor_id
        cursor.execute("UPDATE users SET phone_verified = TRUE, investor_id = %s WHERE phone_number = %s",
                       (investor_id, phone_number))
        conn.commit()

        send_welcome_email(email, investor_id)

        cursor.close()
        conn.close()

        return jsonify({"message": "Phone verified successfully.", "investor_id": investor_id}), 200

    except Exception as e:
        print(f"Error during phone verification: {str(e)}")  # Log the actual error for debugging
        return jsonify({"error": "Phone verification failed"}), 500

def send_welcome_email(email, investor_id):
    try:
        subject = "Welcome to Real One Invest!"
        body = f"""
        Hello,

        Welcome to Real One Invest! Your investor ID is: {investor_id}.

        Thank you for joining us!

        Best regards,
        The Real Invest Team 💼

        Note: This is an automated email. Please do not reply to this email.
        """

        send_email(email, subject, body)
    except Exception as e:
        print(f"❌ Error sending welcome email to {email}: {e}")

@app.route('/api/resend-email-otp', methods=['POST'])
def resend_email_otp():
    try:
        data = request.get_json()
        email = data['email']

        # Check if the user exists in the database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found."}), 404

        # Generate a new OTP and set the expiry time
        new_email_otp = generate_otp()
        otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)

        # Update the OTP and expiry time in the database
        cursor.execute("UPDATE users SET email_otp = %s, email_otp_expiry = %s WHERE email = %s",
                       (new_email_otp, otp_expiry, email))
        conn.commit()

        # Send the new OTP to the user's email
        send_email(email, "Verify Your Email - Real One Invest", f"Your new OTP: {new_email_otp}")

        cursor.close()
        conn.close()

        return jsonify({"message": "New OTP sent successfully."}), 200

    except Exception as e:
        print(f"❌ Error resending email OTP: {str(e)}")
        return jsonify({"error": "Failed to resend OTP."}), 500

@app.route('/api/resend-phone-otp', methods=['POST'])
def resend_phone_otp():
    try:
        data = request.get_json()
        phone_number = data['phone_number']

        # Check if the user exists in the database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT phone_number FROM users WHERE phone_number = %s", (phone_number,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found."}), 404

        # Generate a new OTP and set the expiry time
        new_phone_otp = generate_otp()
        otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)

        # Update the OTP and expiry time in the database
        cursor.execute("UPDATE users SET phone_otp = %s, phone_otp_expiry = %s WHERE phone_number = %s",
                       (new_phone_otp, otp_expiry, phone_number))
        conn.commit()

        # Send the new OTP to the user's phone via SMS
        send_sms(phone_number, new_phone_otp)

        cursor.close()
        conn.close()

        return jsonify({"message": "New OTP sent successfully."}), 200

    except Exception as e:
        print(f"❌ Error resending phone OTP: {str(e)}")
        return jsonify({"error": "Failed to resend OTP."}), 500



@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password, email_verified, phone_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found."}), 404

        db_password, email_verified, phone_verified = user

        if not email_verified:
            return jsonify({"error": "Email not verified."}), 403

        if not phone_verified:
            return jsonify({"error": "Phone not verified."}), 403

        if not check_password_hash(db_password, password):
            return jsonify({"error": "Invalid credentials."}), 401

        access_token = create_access_token(identity=email)
        return jsonify({"message": "Login successful.", "access_token": access_token}), 200

    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        identifier = data['identifier']  # This can be either email or phone number

        # Check if the identifier is an email or phone number
        if "@" in identifier:  # Email check
            column = 'email'
            otp_column = 'email_otp'
            otp_expiry_column = 'email_otp_expiry'
            value = identifier
        else:  # Assume it's a phone number
            column = 'phone_number'
            otp_column = 'phone_otp'
            otp_expiry_column = 'phone_otp_expiry'
            value = identifier

        # Check if the user exists in the database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {column} FROM users WHERE {column} = %s", (value,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": f"User with {column} not found."}), 404

        # Generate OTP and set expiry time
        reset_otp = generate_otp()
        otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)

        # Update OTP and expiry time in the database
        cursor.execute(f"UPDATE users SET {otp_column} = %s, {otp_expiry_column} = %s WHERE {column} = %s",
                       (reset_otp, otp_expiry, value))
        conn.commit()

        # Send the OTP to the user's email or phone
        if column == 'email':
            send_email(value, "Password Reset OTP - Real One Invest", f"Your OTP to reset your password: {reset_otp}")
        else:
            send_sms(value, reset_otp)

        cursor.close()
        conn.close()

        return jsonify({"message": "Password reset OTP sent."}), 200

    except Exception as e:
        print(f"❌ Error in forgot-password: {str(e)}")
        return jsonify({"error": "Failed to send OTP for password reset."}), 500



@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        identifier = data['identifier']  # This can be either email or phone number
        otp = data['otp']
        new_password = data['new_password']

        # Check if the identifier is an email or phone number
        if "@" in identifier:  # Email check
            column = 'email'
            otp_column = 'email_otp'
            otp_expiry_column = 'email_otp_expiry'
        else:  # Assume it's a phone number
            column = 'phone_number'
            otp_column = 'phone_otp'
            otp_expiry_column = 'phone_otp_expiry'

        # Check if the user exists and fetch the stored OTP
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {otp_column}, {otp_expiry_column} FROM users WHERE {column} = %s", (identifier,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": f"User with {column} not found."}), 404

        stored_otp, otp_expiry = user

        # Check if OTP is expired
        if datetime.datetime.now() > otp_expiry:
            return jsonify({"error": "OTP has expired."}), 400

        # Verify the OTP
        if stored_otp != otp:
            return jsonify({"error": "Invalid OTP."}), 400

        # Update the password
        hashed_password = generate_password_hash(new_password)
        cursor.execute(f"UPDATE users SET password = %s WHERE {column} = %s", (hashed_password, identifier))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Password reset successful."}), 200

    except Exception as e:
        print(f"❌ Error in reset-password: {str(e)}")
        return jsonify({"error": "Failed to reset password."}), 500



if __name__ == '__main__':
    create_users_table()
    app.run(debug=True, host="0.0.0.0", port=5000)
