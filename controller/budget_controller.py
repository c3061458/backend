from flask import jsonify, session
from flask_jwt_extended import get_jwt_identity

class Budget:
    def create_budget(self, mysql, data):
        user_id = get_jwt_identity()
    
        # Validate input data
        budget = data.get('budget')

        if budget is None:
            return jsonify({"error": "Budget amount is required"}), 400

        # Create a cursor object
        cursor = mysql.connection.cursor()

        try:
            # Insert the budget into the database
            cursor.execute('''
                INSERT INTO budgets (user_id, budget)
                VALUES (%s, %s)
            ''', (user_id, budget))
            
            # Commit the transaction
            mysql.connection.commit()
            
            return jsonify({"message": "Budget created successfully"}), 201

        except Exception as e:
            # Rollback in case of error
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            # Close the cursor
            cursor.close()
    
    def update_budget(self, mysql, data, budget_id):
        # Extract user_id from JWT token
        user_id = get_jwt_identity()

        # Validate input data
        new_budget = data.get('budget')

        if new_budget is None:
            return jsonify({"error": "New budget amount is required"}), 400

        # Create a cursor object
        cursor = mysql.connection.cursor()

        try:
            # Check if the budget exists and belongs to the user
            cursor.execute('''
                SELECT budget_id FROM budgets 
                WHERE budget_id = %s AND user_id = %s
            ''', (budget_id, user_id))
            
            result = cursor.fetchone()
            
            if not result:
                return jsonify({"error": "Budget not found or access denied"}), 404

            # Update the budget in the database
            cursor.execute('''
                UPDATE budgets 
                SET budget = %s
                WHERE budget_id = %s AND user_id = %s
            ''', (new_budget, budget_id, user_id))
            
            mysql.connection.commit()
            
            return jsonify({"message": "Budget updated successfully"}), 200

        except Exception as e:
            # Rollback in case of error
            mysql.connection.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            # Close the cursor
            cursor.close()
    
    def get_budget(self, mysql):
        # Extract user_id from JWT token
        user_id = get_jwt_identity()

        # Create a cursor object
        cursor = mysql.connection.cursor()

        try:
            # Fetch budget details from the database
            cursor.execute('''
                SELECT budget_id, budget, created_at, updated_at 
                FROM budgets 
                WHERE user_id = %s
            ''', (user_id,))
            
            budgets = cursor.fetchall()

            if not budgets:
                return jsonify({"message": "No budget found for this user"}), 404

            # Prepare the response data
            budget_list = []
            for budget in budgets:
                budget_list.append({
                    "budget_id": budget[0],
                    "budget": budget[1],
                    "created_at": budget[2],
                    "updated_at": budget[3]
                })

            return jsonify({"budgets": budget_list}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            # Close the cursor
            cursor.close()

    def delete_budget(self, mysql):
        pass