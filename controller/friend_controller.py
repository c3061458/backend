from flask import jsonify, session
import random
from flask_jwt_extended import get_jwt_identity

class Friend:
    def add_friend(self, mysql, data):
        friend_mobile = data.get('mobile')

        if not friend_mobile:
            return jsonify({"error": "Friend's mobile number is required"}), 400

        user_one = get_jwt_identity()

        cursor = mysql.connection.cursor()

        try:
            # Fetch the friend's user_id by mobile
            cursor.execute("SELECT user_id FROM users WHERE mobile = %s and is_verified = 1", (friend_mobile,))
            friend = cursor.fetchone()

            if not friend:
                return jsonify({"error": "User with this mobile number does not exist"}), 200

            user_two = friend[0]

            # Check if the friendship already exists
            cursor.execute('''SELECT * FROM friends 
                            WHERE (user_one = %s AND user_two = %s) 
                                OR (user_one = %s AND user_two = %s)''', 
                            (user_one, user_two, user_two, user_one))
            existing_friendship = cursor.fetchone()

            if existing_friendship:
                return jsonify({"message": "You are already friends"}), 200

            # Insert the friendship into the friends table
            cursor.execute('''INSERT INTO friends (user_one, user_two) 
                            VALUES (%s, %s)''', 
                            (user_one, user_two))

            mysql.connection.commit()

            return jsonify({"message": "Friend added successfully"}), 201

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def get_friends(self, mysql):
        user_id = get_jwt_identity()

        cursor = mysql.connection.cursor()

        try:
            # Fetch the friend's user_ids
            cursor.execute('''SELECT 
                                CASE 
                                    WHEN user_one = %s THEN user_two 
                                    ELSE user_one 
                                END AS friend_id 
                            FROM friends 
                            WHERE user_one = %s OR user_two = %s''', 
                            (user_id, user_id, user_id))
            friends = cursor.fetchall()

            if not friends:
                return jsonify({"message": "No friends found"}), 404

            # Fetch details of each friend
            friend_ids = [friend[0] for friend in friends]
            cursor.execute('''SELECT user_id, user_name, email, mobile, gender, birth_date 
                            FROM users 
                            WHERE user_id IN (%s)''' % ','.join(map(str, friend_ids)))
            data = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]
            friend_details = []
            
            for row in data:
                friend_detail = dict(zip(column_names, row))
                friend_details.append(friend_detail)
            
            return jsonify({"friends": friend_details}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def get_friend_by_mobile(self, mysql, mobile):
        user_id = get_jwt_identity()

        cursor = mysql.connection.cursor()

        try:
            cursor.execute('''SELECT user_id, user_name, email, mobile, gender, birth_date 
                            FROM users 
                            WHERE mobile = %s''', (mobile,))
            data = cursor.fetchone()
            
            if not data:
                return jsonify({"message": "No friends found"}), 404

            column_names = [col[0] for col in cursor.description]
         
            friend_details = dict(zip(column_names, data))
            
            return jsonify({"friend": friend_details}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
  
    def get_non_member_friends(self, mysql, group_id):
        created_by = get_jwt_identity()

        cursor = mysql.connection.cursor()

        try:
            # Fetch group details and check if the user is the creator
            cursor.execute('''SELECT created_by FROM user_groups WHERE group_id = %s and created_by = %s''', (group_id, created_by))
            group = cursor.fetchone()

            if not group:
                return jsonify({"error": "Group not found"}), 404

            # Fetch the group members
            cursor.execute('''SELECT member_id FROM group_members WHERE group_id = %s''', (group_id,))
            group_members = cursor.fetchall()
            member_ids = [member[0] for member in group_members]

            # Fetch the creator's friends
            cursor.execute('''SELECT user_one AS friend_id FROM friends WHERE user_two = %s
                            UNION 
                            SELECT user_two AS friend_id FROM friends WHERE user_one = %s''',
                        (created_by, created_by))
            friends = cursor.fetchall()
            friend_ids = [friend[0] for friend in friends]

            # Get friends who are not group members
            non_member_friends = [friend_id for friend_id in friend_ids if friend_id not in member_ids]

            if non_member_friends:
                # Fetch details of the non-member friends
                cursor.execute('''SELECT user_id, user_name, email, mobile, gender FROM users WHERE user_id IN %s''',
                            (tuple(non_member_friends),))
                non_member_friend_details = cursor.fetchall()
                
                column_names = [col[0] for col in cursor.description]
                friend_details = []
                
                for row in non_member_friend_details:
                    friend_detail = dict(zip(column_names, row))
                    friend_details.append(friend_detail)

                return jsonify({"friends": friend_details, "message": "success"}), 200
            else:
                return jsonify({"message": "No friends found who are not in the group"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
