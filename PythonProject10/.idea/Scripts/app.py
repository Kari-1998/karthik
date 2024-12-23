
import os
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

# Function to create or update the users table
def create_users_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # SQL query to create the users table with the reset_token, otp, and otp_expiry columns
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL,
            phone_number VARCHAR(15),
            address TEXT,
            reset_token VARCHAR(255),
            otp VARCHAR(6),
            otp_expiry TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        conn.commit()

        print("Table 'users' created or updated successfully.")

        cursor.close()
        conn.close()

    except (Exception, psycopg2.Error) as error:
        print(f"Error while creating or updating the table: {error}")


# Initialize Flask app
app = Flask(__name__)

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

        if password != reenter_password:
            return jsonify({"error": "Passwords do not match."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO users (first_name, last_name, email, password, phone_number, address)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (first_name, last_name, email, password, phone_number, address))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "User stored successfully."}), 201

    except (Exception, psycopg2.Error) as error:
        print(f"Error while storing user data: {error}")
        return jsonify({"error": "Failed to store user data."}), 500

# API endpoint to login with email and password
@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()

        email = data.get('email')
        password = data.get('password')

        if not (email and password):
            return jsonify({"error": "Email and password are required."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        select_query = "SELECT password FROM users WHERE email = %s"
        cursor.execute(select_query, (email,))
        user_record = cursor.fetchone()

        cursor.close()
        conn.close()

        if user_record:
            stored_password = user_record[0]
            if password == stored_password:
                return jsonify({"message": "Login successful."}), 200
            else:
                return jsonify({"error": "Invalid email or password."}), 401
        else:
            return jsonify({"error": "User not found."}), 404

    except (Exception, psycopg2.Error) as error:
        print(f"Error while logging in: {error}")
        return jsonify({"error": "Failed to log in."}), 500

# API endpoint for forgot password
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({"error": "Email is required."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        select_query = "SELECT id, first_name FROM users WHERE email = %s"
        cursor.execute(select_query, (email,))
        user_record = cursor.fetchone()

        if not user_record:
            cursor.close()
            conn.close()
            return jsonify({"error": "User not found."}), 404

        user_id, first_name = user_record

        # Generate a secure reset token
        reset_token = str(uuid.uuid4())

        # Update the reset token in the database
        update_query = "UPDATE users SET reset_token = %s WHERE id = %s"
        cursor.execute(update_query, (reset_token, user_id))
        conn.commit()

        reset_link = f"http://127.0.0.1:5000/api/reset-password/{reset_token}"

        # Email content
        subject = "Password Reset Request"
        body = f"Hello {first_name},\n\nClick the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, please ignore this email."

        send_email(email, subject, body)
        cursor.close()
        conn.close()

        return jsonify({"message": "Password reset link has been sent to your email address. Check your inbox."}), 200

    except (Exception, psycopg2.Error) as error:
        print(f"Error while processing forgot password: {error}")
        return jsonify({"error": "Failed to process the request."}), 500

# Function to send email using Google App Password
def send_email(to_email, subject, body):
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'X')
    APP_PASSWORD = os.getenv('APP_PASSWORD', 'X')

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

# Twilio Configuration
TWILIO_ACCOUNT_SID = 'X'
TWILIO_AUTH_TOKEN = 'X'
TWILIO_PHONE_NUMBER = 'X'

def generate_and_send_otp(phone_number):
    try:
        otp = str(random.randint(100000, 999999))
        expiry_time = time.time() + 300  # OTP valid for 5 minutes

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your OTP is {otp}. It is valid for 5 minutes.",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"Twilio API Response: {message.sid}")  # Debug: Print the message SID
        return otp, expiry_time
    except Exception as e:
        print(f"Failed to send OTP. Error: {e}")
        return None, None


# API endpoint for forgot password via phone number
@app.route('/api/forgot-password-phone', methods=['POST'])
def forgot_password_phone():
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')

        if not phone_number:
            return jsonify({"error": "Phone number is required."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        select_query = "SELECT id FROM users WHERE phone_number = %s"
        cursor.execute(select_query, (phone_number,))
        user_record = cursor.fetchone()

        if not user_record:
            cursor.close()
            conn.close()
            return jsonify({"error": "User not found."}), 404

        user_id = user_record[0]

        # Generate and send OTP
        otp, otp_expiry = generate_and_send_otp(phone_number)
        if not otp:
            return jsonify({"error": "Failed to send OTP. Please try again."}), 500

        # Update OTP and expiry in the database
        update_query = "UPDATE users SET otp = %s, otp_expiry = to_timestamp(%s) WHERE id = %s"
        cursor.execute(update_query, (otp, otp_expiry, user_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "OTP has been sent to your phone number."}), 200

    except (Exception, psycopg2.Error) as error:
        print(f"Error while processing forgot password via phone: {error}")
        return jsonify({"error": "Failed to process the request."}), 500

# API endpoint to verify OTP and reset password
@app.route('/api/reset-password-phone', methods=['POST'])
def reset_password_phone():
    try:
        data = request.get_json()

        phone_number = data.get('phone_number')
        otp = data.get('otp')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not (phone_number and otp and new_password and confirm_password):
            return jsonify({"error": "All fields are required."}), 400

        if new_password != confirm_password:
            return jsonify({"error": "Passwords do not match."}), 400

        conn = get_connection()
        cursor = conn.cursor()

        select_query = "SELECT id, otp, otp_expiry FROM users WHERE phone_number = %s"
        cursor.execute(select_query, (phone_number,))
        user_record = cursor.fetchone()

        if not user_record:
            cursor.close()
            conn.close()
            return jsonify({"error": "User not found."}), 404

        user_id, stored_otp, otp_expiry = user_record

        if otp != stored_otp:
            return jsonify({"error": "Invalid OTP."}), 400

        if time.time() > otp_expiry.timestamp():
            return jsonify({"error": "OTP has expired."}), 400

        # Update password in the database
        update_query = "UPDATE users SET password = %s, otp = NULL, otp_expiry = NULL WHERE id = %s"
        cursor.execute(update_query, (new_password, user_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Password reset successfully."}), 200

    except (Exception, psycopg2.Error) as error:
        print(f"Error while resetting password via phone: {error}")
        return jsonify({"error": "Failed to reset password."}), 500


# Run the Flask app
if __name__ == '__main__':
    create_users_table()
    app.run(debug=True, host="0.0.0.0", port=5000)
