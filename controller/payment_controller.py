from flask import jsonify, session
from flask_jwt_extended import get_jwt_identity
#import pytesseract
from PIL import Image
#import cv2
import easyocr
#import boto3
import requests
#import re

class Payment:
    def create_payment(self, mysql, data):
        created_by = get_jwt_identity()
        total_amount = data.get('amount')
        description = data.get('description')
        splits = data.get('splits')  # Expected to be a list of dictionaries

        if not total_amount or not splits:
            return jsonify({"error": "Amount and splits are required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Insert payment record
            cursor.execute('''INSERT INTO payments (amount, description, created_by) VALUES (%s, %s, %s)''', 
                            (total_amount, description, created_by))
            payment_id = cursor.lastrowid

            # total_splits_amount = 0
            # user_ids = set()

            for split in splits:
                user_id = split.get('user_id')
                group_id = split.get('group_id')
                split_amount = split.get('amount')

                if not split_amount:
                    return jsonify({"error": "Amount for each split is required"}), 400

                if group_id:  # Split among all users in a group
                    cursor.execute('''SELECT member_id FROM group_members WHERE group_id = %s''', (group_id,))
                    group_members = cursor.fetchall()
                    total_members = len(group_members)
                    per_member_amount = split_amount / total_members

                    for member in group_members:
                        cursor.execute('''INSERT INTO payment_splits (payment_id, user_id, amount) 
                                        VALUES (%s, %s, %s)''', 
                                        (payment_id, member[0], per_member_amount))
                        # user_ids.add(member['user_id'])
                    
                    cursor.execute('''UPDATE payment_splits 
                          SET is_paid = 1, updated_at = NOW() 
                          WHERE payment_id = %s AND user_id = %s''', 
                          (payment_id, created_by))
                    
                elif user_id:  # Split among specified users
                    user_list = user_id if isinstance(user_id, list) else [user_id]
                    for uid in user_list:
                        cursor.execute('''INSERT INTO payment_splits (payment_id, user_id, amount) 
                                        VALUES (%s, %s, %s)''', 
                                        (payment_id, uid, split_amount / len(user_list)))
                        # user_ids.add(uid)
                    
                    cursor.execute('''UPDATE payment_splits 
                          SET is_paid = 1, updated_at = NOW() 
                          WHERE payment_id = %s AND user_id = %s''', 
                          (payment_id, created_by))

                # total_splits_amount += split_amount

            # if total_splits_amount != total_amount:
            #     return jsonify({"error": "Total split amount must match the total payment amount"}), 400

            mysql.connection.commit()
            return jsonify({"message": "Payment recorded successfully"}), 201

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def upload_bill(self, image_path):
        
        reader = easyocr.Reader(['en'])
        result = reader.readtext('static/receipt/{}'.format(image_path))
        parsed_text = ' '.join([res[1] for res in result])
        data = self.extract_total_due(text=parsed_text)
        return jsonify({"amount": data}), 200
        
        
        # api_key = 'K89972300488957'
        # image_path = 'static/receipt/{}'.format(image_path)
        
        # with open(image_path, 'rb') as image_file:
        #     response = requests.post(
        #         'https://api.ocr.space/parse/image',
        #         files={'image': (image_path, image_file, 'image/*')},  # Specify the content type
        #         data={
        #                 'apikey': api_key, 
        #                 'isTable': True,
        #             }
        #     )
        
        # result = response.json()
        # parsed_text = result['ParsedResults'][0]['ParsedText']
        # data = self.extract_total_due(text=parsed_text)
        return jsonify({"amount": data}), 200

    def extract_total_due(self, text):
        # Regular expression pattern to find the total due amount
        pattern = r'Amount due\s*([\d,]+\.\d{2})'
        
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            # Extract and return the total amount due
            return match.group(1)
        else:
            pattern = r'Total Due\s*([\d,]+\.\d{2})'

            # Search for the pattern in the text
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                # Extract and return the total amount due
                return match.group(1)
            else:
                pattern = r'TOTAL\t*([\d,]+\,\d{2})'

                match = re.search(pattern, text, re.IGNORECASE)

                if match:
                    return match.group(1)
                else: 
                    pattern = r'Total:\s*([€\d,]+\.\d{2})'

                    match = re.search(pattern, text, re.IGNORECASE)

                    if match:
                        return match.group(1)
                    else: 
                        pattern = r'TOTAL\s*E?\s*([\d,.]+)'
                        
                        match = re.search(pattern, text, re.IGNORECASE)

                        if match:
                            return match.group(1)
                        else:
                            pattern = r'Total:\s*E?\s*([\d,.]+)'
                        
                            match = re.search(pattern, text, re.IGNORECASE)

                            if match:
                                return match.group(1)
                            else:
                                return "Total due amount not found"

