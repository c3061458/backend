from flask import jsonify, session
from flask_jwt_extended import get_jwt_identity

class Group:
    def create_group(self, mysql, data):
        group_name = data.get('group_name')
        created_by = get_jwt_identity()  # Get the user ID from the JWT token

        if not group_name:
            return jsonify({"error": "Group name is required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Insert the new group into the groups table
            cursor.execute('''INSERT INTO user_groups (group_name, created_by) VALUES (%s, %s)''', 
                            (group_name, created_by))
            mysql.connection.commit()
            group_id = cursor.lastrowid
            
            cursor.execute('''INSERT INTO group_members (group_id, member_id) 
                            VALUES (%s, %s)''', 
                            (group_id, created_by))
            mysql.connection.commit()

            return jsonify({"message": "Group created successfully", "group_id": group_id}), 201

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def add_group_member(self, mysql, data):
        group_id = data.get('group_id')
        member_id = data.get('member_id')
        created_by = get_jwt_identity()

        if not group_id or not member_id:
            return jsonify({"error": "Group ID and Member ID are required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Check if the group exists and is created by the current user
            cursor.execute('''SELECT * FROM user_groups WHERE group_id = %s AND created_by = %s''', 
                            (group_id, created_by))
            group = cursor.fetchone()

            if not group:
                return jsonify({"message": "Group not found or you are not the creator"}), 200

              # Check if the member exists in the users table and is verified
            cursor.execute('''SELECT * FROM users WHERE user_id = %s AND is_verified = 1''', 
                            (member_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"message": "User is either not registered 0r not verified"}), 200

            # Check if the member is already in the group
            cursor.execute('''SELECT * FROM group_members WHERE group_id = %s AND member_id = %s''',
                            (group_id, member_id))
            existing_member = cursor.fetchone()

            if existing_member:
                return jsonify({"message": "Member is already in the group"}), 200

            # Insert the new member into the group_members table
            cursor.execute('''INSERT INTO group_members (group_id, member_id) 
                            VALUES (%s, %s)''', 
                            (group_id, member_id))
            mysql.connection.commit()

            return jsonify({"message": "Member added to the group successfully"}), 201

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def add_group_members(self, mysql, data):
        group_id = data.get('group_id')
        member_ids = data.get('member_ids')  # Expecting a list of member IDs
        created_by = get_jwt_identity()

        if not group_id or not member_ids or not isinstance(member_ids, list):
            return jsonify({"message": "Group ID and a list of Member IDs are required"}), 200

        cursor = mysql.connection.cursor()

        try:
            # Check if the group exists and is created by the current user
            cursor.execute('''SELECT * FROM user_groups WHERE group_id = %s AND created_by = %s''', 
                            (group_id, created_by))
            group = cursor.fetchone()

            if not group:
                return jsonify({"message": "Group not found or you are not the creator"}), 200

            # List to track failed additions
            failed_members = []

            for member_id in member_ids:
                # Check if the member exists in the users table and is verified
                cursor.execute('''SELECT * FROM users WHERE user_id = %s AND is_verified = 1''', 
                                (member_id,))
                user = cursor.fetchone()

                if not user:
                    failed_members.append({"member_id": member_id, "error": "User is either not registered or not verified"})
                    continue

                # Check if the member is already in the group
                cursor.execute('''SELECT * FROM group_members WHERE group_id = %s AND member_id = %s''',
                                (group_id, member_id))
                existing_member = cursor.fetchone()

                if existing_member:
                    failed_members.append({"member_id": member_id, "error": "Member is already in the group"})
                    continue

                # Insert the new member into the group_members table
                cursor.execute('''INSERT INTO group_members (group_id, member_id) 
                                VALUES (%s, %s)''', 
                                (group_id, member_id))

            # Commit changes to the database
            mysql.connection.commit()

            # If there are failed members, include them in the response
            if failed_members:
                return jsonify({
                    "message": "Some members could not be added to the group",
                    "failed_members": failed_members
                }), 207  # 207 Multi-Status

            return jsonify({"message": "All members added to the group successfully"}), 201

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def get_group_details(self, mysql, group_id):
        cursor = mysql.connection.cursor()
        
        try:
            # Fetch group details
            cursor.execute('''SELECT ug.group_id, ug.group_name, ug.created_at, 
                                 u.user_id, u.user_name, u.email, u.mobile
                          FROM user_groups ug
                          JOIN users u ON ug.created_by = u.user_id
                          WHERE ug.group_id = %s''', 
                            (group_id,))
            group = cursor.fetchone()

            # print(group)
            if not group:
                return jsonify({"error": "Group not found"}), 404
        
            column_names = [col[0] for col in cursor.description]
            group_details = dict(zip(column_names, group))

            # Fetch members of the group
            cursor.execute('''SELECT gm.member_id, u.user_name, u.email, u.mobile, u.gender 
                            FROM group_members gm 
                            JOIN users u ON gm.member_id = u.user_id 
                            WHERE gm.group_id = %s''', 
                            (group_id,))
            members = cursor.fetchall()
            column_names = [col[0] for col in cursor.description]
            
            member_details = []
            
            for row in members:
                member_detail = dict(zip(column_names, row))
                member_details.append(member_detail)
            
            group_details['members'] = member_details

            return jsonify({"group_details": group_details}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()

    def list_groups(self, mysql):
        user_id = get_jwt_identity() 
        
        cursor = mysql.connection.cursor()

        try:
            # Fetch groups where the user is either the creator or a member
            cursor.execute('''
            SELECT 
                ug.group_id, 
                ug.group_name, 
                ug.created_at, 
                u.user_id AS creator_id, 
                u.user_name AS creator_name, 
                u.email AS creator_email, 
                u.mobile AS creator_mobile, 
                (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = ug.group_id) AS member_count
            FROM user_groups ug
            JOIN users u ON ug.created_by = u.user_id
            WHERE ug.created_by = %s 
            OR ug.group_id IN 
            (SELECT gm.group_id FROM group_members gm WHERE gm.member_id = %s)
                            ''', (user_id, user_id))
            groups = cursor.fetchall()

            if not groups:
                return jsonify({"message": "No groups found"}), 404

            column_names = [col[0] for col in cursor.description]
            
            group_list =  []
            
            for row in groups:
                group = dict(zip(column_names, row))
                group_list.append(group)
            
            return jsonify({"groups": group_list}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            
    def remove_group_member(self, mysql, data):
        group_id = data.get('group_id')
        member_id = data.get('member_id')
        user_id = get_jwt_identity()  # Get the authenticated user's ID

        if not group_id or not member_id:
            return jsonify({"error": "Group ID and Member ID are required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Check if the authenticated user is the creator of the group
            cursor.execute('''SELECT * FROM user_groups WHERE group_id = %s AND created_by = %s''', 
                            (group_id, user_id))
            group = cursor.fetchone()

            if not group:
                return jsonify({"error": "You do not have permission to remove members from this group"}), 403

            # Check if the member is actually in the group
            cursor.execute('''SELECT * FROM group_members WHERE group_id = %s AND member_id = %s''', 
                            (group_id, member_id))
            member = cursor.fetchone()

            if not member:
                return jsonify({"error": "Member not found in the group"}), 404

            # Remove the member from the group
            cursor.execute('''DELETE FROM group_members WHERE group_id = %s AND member_id = %s''', 
                            (group_id, member_id))
            mysql.connection.commit()

            return jsonify({"message": "Member removed from the group successfully"}), 200

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
                
    def delete_group(self, mysql, data):
        group_id = data.get('group_id')
        user_id = get_jwt_identity()  # Get the authenticated user's ID

        if not group_id:
            return jsonify({"error": "Group ID is required"}), 400

        cursor = mysql.connection.cursor()

        try:
            # Check if the authenticated user is the creator of the group
            cursor.execute('''SELECT * FROM user_groups WHERE group_id = %s AND created_by = %s''', 
                            (group_id, user_id))
            group = cursor.fetchone()

            if not group:
                return jsonify({"error": "You do not have permission to delete this group"}), 403

            # Delete all members from the group
            cursor.execute('''DELETE FROM group_members WHERE group_id = %s''', 
                            (group_id,))
            
            # Delete the group
            cursor.execute('''DELETE FROM user_groups WHERE group_id = %s''', 
                            (group_id,))
            
            mysql.connection.commit()

            return jsonify({"message": "Group deleted successfully"}), 200

        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()