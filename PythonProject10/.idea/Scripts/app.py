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
import time
from twilio.rest import Client

# Define the database connection parameters
def get_connection():
    return psycopg2.connect(
        dbname="realoneinvest",
        user="karthik1",
        password="Info123tech",
        host="localhost",
        port="5433"
    )

# Function to create or update the users and general_admins tables
def create_tables():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # SQL query to create the users table with composite primary keys (investor_id and euid)
        create_users_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            investor_id VARCHAR(20),
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
            PRIMARY KEY (investor_id, euid)
        );
        """
        cursor.execute(create_users_table_query)

        # SQL query to create the general_admins table
        create_general_admins_table_query = """
        CREATE TABLE IF NOT EXISTS general_admins (
            id SERIAL PRIMARY KEY,
            general_admin_id VARCHAR(20) UNIQUE,
            investor_id VARCHAR(20) NOT NULL,
            FOREIGN KEY (investor_id) REFERENCES users (investor_id) ON DELETE CASCADE
        );
        """
        cursor.execute(create_general_admins_table_query)

        conn.commit()
        print("Tables 'users' and 'general_admins' created or updated successfully.")

        cursor.close()
        conn.close()

        # Print the contents of the tables
        print_table_contents()

    except (Exception, psycopg2.Error) as error:
        print(f"Error while creating or updating the tables: {error}")

# Function to print table contents in the console
def print_table_contents():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch and print the users table
        print("\nContents of 'users' table:")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        for user in users:
            print(user)

        # Fetch and print the general_admins table
        print("\nContents of 'general_admins' table:")
        cursor.execute("SELECT * FROM general_admins")
        admins = cursor.fetchall()
        for admin in admins:
            print(admin)

        cursor.close()
        conn.close()

    except (Exception, psycopg2.Error) as error:
        print(f"Error while fetching table contents: {error}")

# Initialize Flask app
app = Flask(__name__)

# Function to validate email format
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

# Function to validate phone number format
def is_valid_phone_number(phone_number):
    return phone_number.isdigit() and len(phone_number) == 10

# Generate unique investor ID
def generate_investor_id():
    return f"I{random.randint(1000, 9999)}"

# Generate unique general admin ID
def generate_general_admin_id():
    return f"GA{random.randint(1000, 9999)}"

# Generate unique EUID (UUID-based)
def generate_euid():
    return str(uuid.uuid4())

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

        if len(first_name) < 2 or len(last_name) < 2:
            return jsonify({"error": "First name and last name must have at least 2 characters."}), 400

        if not is_valid_phone_number(phone_number):
            return jsonify({"error": "Phone number must be exactly 10 digits."}), 400

        if password != reenter_password:
            return jsonify({"error": "Passwords do not match."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Generate a unique investor ID and EUID
        investor_id = generate_investor_id()
        euid = generate_euid()

        # Insert user data into the database
        insert_query = """
        INSERT INTO users (investor_id, euid, first_name, last_name, email, password, phone_number, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (investor_id, euid, first_name, last_name, email, password, phone_number, address))
        conn.commit()

        cursor.close()
        conn.close()

        # Send a welcome email
        subject = "Welcome to RealOneInvest!"
        body = f"Hello {first_name} {last_name},\n\nThank you for signing up with RealOneInvest! We’re excited to have you on board.\n\nBest regards,\nThe RealOneInvest Team"
        send_email(email, subject, body)

        return jsonify({"message": "User stored successfully and welcome email sent.", "investor_id": investor_id, "euid": euid}), 201

    except (Exception, psycopg2.Error) as error:
        print(f"Error while storing user data: {error}")
        return jsonify({"error": "Failed to store user data."}), 500

# Function to send email using Google App Password
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
        print(f"Failed to send email. Error: {e}")

# Run the Flask app
if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host="0.0.0.0", port=5000)
