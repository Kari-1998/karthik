import os
import re
import psycopg2
from psycopg2 import sql
from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
import random
from functools import wraps

# Define the database connection parameters
def get_connection():
    return psycopg2.connect(
        dbname="realoneinvest",
        user="karthik1",
        password="Info123tech",
        host="localhost",
        port="5433"
    )

# Function to create or update the users table (removed general_admins table)
def create_tables():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Create the users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            investor_id VARCHAR(20) Unique,
            euid UUID,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL,
            phone_number VARCHAR(15),
            address TEXT,
            reset_token VARCHAR(255),
            otp VARCHAR(6),
            otp_expiry TIMESTAMP,
            PRIMARY KEY (euid)
        );
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("Users table created successfully.")

    except (Exception, psycopg2.Error) as error:
        print(f"Error creating tables: {error}")

# Initialize Flask app
app = Flask(__name__)

# Email validation
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email) is not None

# Phone number validation
def is_valid_phone_number(phone_number):
    return phone_number.isdigit() and len(phone_number) == 10

# Generate unique IDs
def generate_investor_id():
    return f"I{random.randint(1000, 9999)}"

def generate_euid():
    return str(uuid.uuid4())

# Function to send email
def send_email(to_email, subject, body):
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'pothi9940@gmail.com')
    APP_PASSWORD = os.getenv('APP_PASSWORD', 'vive mscg vola ajso')

    try:
        message = MIMEMultipart()
        message['From'] = EMAIL_ADDRESS
        message['To'] = to_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, message.as_string())
        print(f"Email sent successfully to {to_email}")
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

# API endpoint to store user data
@app.route('/api/signup', methods=['POST'])
def store_user():
    try:
        data = request.get_json()

        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        password = data.get('password')
        reenter_password = data.get('reenter_password')
        phone_number = data.get('phone_number')
        address = data.get('address')

        if not (first_name and last_name and email and password and reenter_password):
            return jsonify({"error": "All required fields must be provided."}), 400

        if not is_valid_email(email):
            return jsonify({"error": "Invalid email format."}), 400

        if not is_valid_phone_number(phone_number):
            return jsonify({"error": "Phone number must be exactly 10 digits."}), 400

        if password != reenter_password:
            return jsonify({"error": "Passwords do not match."}), 400

        investor_id = generate_investor_id()
        euid = generate_euid()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users (investor_id, euid, first_name, last_name, email, password, phone_number, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (investor_id, euid, first_name, last_name, email, password, phone_number, address))
        conn.commit()
        cursor.close()
        conn.close()

        subject = "Welcome to RealOneInvest!"
        body = f"Hello {first_name},\n\nThank you for signing up with RealOneInvest!"
        send_email(email, subject, body)

        return jsonify({"message": "User registered successfully."}), 201

    except (Exception, psycopg2.Error) as error:
        print(f"Error storing user data: {error}")
        return jsonify({"error": "Failed to store user data."}), 500

# Run the app
if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host="0.0.0.0", port=5000)
