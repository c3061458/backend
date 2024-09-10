from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import os
import sys
from flask_bcrypt import Bcrypt 
import datetime
from flask_jwt_extended import JWTManager, jwt_required
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'controller')))

from sendmail import SendMail
from user_controller import User
from friend_controller import Friend
from group_controller import Group
from payment_controller import Payment
from budget_controller import Budget
from transaction_controller import Transaction

app = Flask('__main__')

app.config['JWT_SECRET_KEY'] = '453dgdfg75fg'
app.secret_key = "xvdv446546fdf"

app.config['MYSQL_USER'] = "root"
app.config["MYSQL_PASSWORD"] = "1234"
app.config["MYSQL_DB"] = "splite_mate"

app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

mysql = MySQL(app)
bcrypt = Bcrypt(app) 
jwt = JWTManager(app)

UPLOAD_PROFILE = 'static/profile'
UPLOAD_RECEIPT = 'static/receipt'

app.config['UPLOAD_PROFILE'] = UPLOAD_PROFILE
app.config['UPLOAD_RECEIPT'] = UPLOAD_RECEIPT

user_instance = User()
friend_instance = Friend()
group_instance = Group()
payment_instance = Payment()
budget_instance = Budget()
transaction_instance = Transaction()

@app.route('/register', methods=['POST'])
def home():
    data = request.json
    return user_instance.register(mysql=mysql, data=data, bcrypt=bcrypt)

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json
    return user_instance.verify_otp(mysql=mysql, input_data=data)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    return user_instance.login(mysql=mysql, data=data, bcrypt=bcrypt)

@app.route('/change_password', methods=['POST'])
@jwt_required()
def change_password():
    data = request.json
    return user_instance.change_password(mysql=mysql, data=data, bcrypt=bcrypt)

@app.route('/change_security_pin', methods=['POST'])
@jwt_required()
def change_security_pin():
    data = request.json
    return user_instance.change_security_pin(mysql=mysql, data=data, bcrypt=bcrypt)

@app.route('/add_friend', methods=['POST'])
@jwt_required()
def add_friend():
    data = request.json
    return friend_instance.add_friend(mysql=mysql, data=data)

@app.route('/get_friends', methods=['GET'])
@jwt_required()
def get_friends():
    return friend_instance.get_friends(mysql=mysql)

@app.route('/get_friend_by_mobile/<int:mobile>', methods=['GET'])
@jwt_required()
def get_friend_by_mobile(mobile):
    return friend_instance.get_friend_by_mobile(mysql=mysql, mobile=mobile)

@app.route('/non_group_member_friends/<int:group_id>', methods=['GET'])
@jwt_required()
def non_group_member_friends(group_id):
    return friend_instance.get_non_member_friends(mysql=mysql, group_id=group_id)

@app.route('/create_group', methods=['POST'])
@jwt_required()
def create_group():
    data = request.json
    return group_instance.create_group(mysql=mysql, data=data)

@app.route('/add_group_member', methods=['POST'])
@jwt_required()
def add_group_member():
    data = request.json
    return group_instance.add_group_member(mysql=mysql, data=data)

@app.route('/add_group_members', methods=['POST'])
@jwt_required()
def add_group_members():
    data = request.json
    return group_instance.add_group_members(mysql=mysql, data=data)

@app.route('/get_group_details/<int:group_id>', methods=['GET'])
@jwt_required()
def get_group_details(group_id):
    return group_instance.get_group_details(mysql=mysql, group_id=group_id)

@app.route('/list_groups', methods=['GET'])
@jwt_required()
def list_groups():
    return group_instance.list_groups(mysql=mysql)

@app.route('/remove_group_member', methods=['POST'])
@jwt_required()
def remove_group_member():
    data = request.json
    return group_instance.remove_group_member(mysql=mysql, data=data)

@app.route('/delete_group', methods=['DELETE'])
@jwt_required()
def delete_group():
    data = request.json
    return group_instance.delete_group(mysql=mysql, data=data)

@app.route('/create_payment', methods=['POST'])
@jwt_required()
def create_payment():
    data = request.json
    return payment_instance.create_payment(mysql=mysql, data=data)

@app.route('/upload_bill', methods=['POST'])
@jwt_required()
def upload_bill():
    if 'bill_image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    bill_image = request.files['bill_image']
    
    fileName = bill_image.filename
    bill_image.save(os.path.join(app.config['UPLOAD_RECEIPT'], fileName))
    
    return payment_instance.upload_bill(image_path=fileName)

@app.route('/create_budget', methods=['POST'])
@jwt_required()  
def create_budget():
    data = request.json
    return budget_instance.create_budget(mysql=mysql, data=data)

@app.route('/fetch_budget', methods=['GET'])
@jwt_required()  # Protect this route with JWT
def fetch_budget():
    return budget_instance.get_budget(mysql=mysql)

@app.route('/update_budget/<int:budget_id>', methods=['PUT'])
@jwt_required()  # Protect this route with JWT
def update_budget(budget_id):
    data = request.json
    return budget_instance.update_budget(mysql=mysql, data=data, budget_id=budget_id)

@app.route('/get_transactions', methods=['GET'])
@jwt_required()  # Protect this route with JWT
def get_transactions():
    return transaction_instance.get_transactions(mysql=mysql)

@app.route('/get_accounts', methods=['GET'])
@jwt_required()  # Protect this route with JWT
def get_accounts():
    return transaction_instance.get_accounts(mysql=mysql)

@app.route('/get_home_transactions', methods=['GET'])
@jwt_required()  # Protect this route with JWT
def get_home_transactions():
    return transaction_instance.get_home_transactions(mysql=mysql)

@app.route('/get_total_amount_current_month', methods=['GET'])
@jwt_required()  # Protect this route with JWT
def get_total_amount_current_month():
    return transaction_instance.get_total_amount_current_month(mysql=mysql)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=3000)