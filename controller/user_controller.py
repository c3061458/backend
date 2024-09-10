import os
import sys
from flask import jsonify, session
import random
from flask_jwt_extended import create_access_token, get_jwt_identity

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))

from sendmail import SendMail

mail_obj = SendMail()

class User:
    def register(self, mysql, data, bcrypt):
        user_name = data.get('user_name')
        email = data.get('email')
        mobile = data.get('mobile')
        password = data.get('password')
        security_pin = data.get('security_pin')
        gender = data.get('gender')
        birth_date = data.get('birth_date')

        # Input validation
        if not all([user_name, email, mobile, password, security_pin, gender, birth_date]):
            return jsonify({"error": "All fields are required"}), 400

        # Encrypt the password and security pin
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        hashed_security_pin = bcrypt.generate_password_hash(str(security_pin)).decode('utf-8')

        # Create a cursor object
        cursor = mysql.connection.cursor()

        try:
            # Insert user into the database
            cursor.execute('''INSERT INTO users (user_name, email, mobile, password, security_pin, gender, birth_date) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                           (user_name, email, mobile, hashed_password, hashed_security_pin, gender, birth_date))
            mysql.connection.commit()

            # Generate OTP
            otp = random.randint(100000, 999999)

            # Insert or update OTP in the database
            cursor.execute('''INSERT INTO otp_verifications (email, otp) 
                              VALUES (%s, %s)
                              ON DUPLICATE KEY UPDATE otp = %s, created_at = CURRENT_TIMESTAMP''', 
                           (email, otp, otp))
            mysql.connection.commit()

            # Send OTP to user's email
            mail_obj.sendMail(email=email, otp=otp)

            return jsonify({"message": "User registered successfully. OTP sent to your email."}), 201

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
        
    def verify_otp(self, mysql, input_data):
        email = input_data.get('email')
        input_otp = input_data.get('otp')
        
        print(email)
        print(input_otp)

        if not all([email, input_otp]):
            return jsonify({"error": "Email and OTP are required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Retrieve OTP from the database
            cursor.execute('''SELECT otp FROM otp_verifications WHERE email = %s''', (email,))
            otp_entry = cursor.fetchone()

            if otp_entry and otp_entry[0] == int(input_otp):
                # OTP is valid, now verify the user
                cursor.execute('''UPDATE users SET is_verified = 1 WHERE email = %s''', (email,))
                mysql.connection.commit()

                # Delete the OTP record after successful verification
                cursor.execute('''DELETE FROM otp_verifications WHERE email = %s''', (email,))
                mysql.connection.commit()

                return jsonify({"message": "OTP verified successfully. User is now verified."}), 200
            else:
                return jsonify({"error": "Invalid OTP or email."}), 400

        except Exception as e:
            mysql.connection.rollback()
            print(str(e))
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def login(self, mysql, data, bcrypt):
        mobile = data.get('mobile')
        password = data.get('password')

        if not mobile or not password:
            return jsonify({"error": "Mobile and password are required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Fetch the user details by mobile
            cursor.execute("SELECT * FROM users WHERE mobile = %s", (mobile,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "Invalid mobile number"}), 401

            # Check the password
            if not bcrypt.check_password_hash(user[4], password):
                return jsonify({"error": "Invalid password"}), 401
            
            user_id = user[0]
            
            # Create JWT token
            token = create_access_token(identity=user_id)
            # Prepare user details without the password
            user_details = {
                "user_id": user[0],
                "user_name": user[1],
                "email": user[2],
                "mobile": user[3],
                "gender": user[6],
                "birth_date": user[6]
            }

            print(user_details)

            return jsonify({"token": token, "user": user_details}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def change_password(self, mysql, data, bcrypt):
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({"error": "Current password and new password are required"}), 400

        user_id = get_jwt_identity()

        cursor = mysql.connection.cursor()

        try:
            # Fetch the user by ID
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Check if the current password is correct
            if not bcrypt.check_password_hash(user[4], current_password):
                return jsonify({"error": "Incorrect current password"}), 401

            # Hash the new password
            hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

            # Update the password in the database
            cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (hashed_new_password, user_id))
            mysql.connection.commit()

            return jsonify({"message": "Password changed successfully"}), 200

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
    
    def change_security_pin(self, mysql, data, bcrypt):
        current_security_pin = data.get('current_security_pin')
        new_security_pin = data.get('new_security_pin')

        if not current_security_pin or not new_security_pin:
            return jsonify({"error": "Current security pin and new security pin are required"}), 400

        user_id = get_jwt_identity()

        cursor = mysql.connection.cursor()

        try:
            # Fetch the user by ID
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Check if the current security pin is correct
            if not bcrypt.check_password_hash(user[5], str(current_security_pin)):
                return jsonify({"error": "Incorrect current security pin"}), 401

            # Hash the new security pin
            hashed_new_security_pin = bcrypt.generate_password_hash(str(new_security_pin)).decode('utf-8')

            # Update the security pin in the database
            cursor.execute("UPDATE users SET security_pin = %s WHERE user_id = %s", (hashed_new_security_pin, user_id))
            mysql.connection.commit()

            return jsonify({"message": "Security pin changed successfully"}), 200

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    