from flask import jsonify, session
from flask_jwt_extended import get_jwt_identity
from collections import defaultdict

class Transaction:
    def get_transactions(self, mysql):
        user_id = get_jwt_identity()
        cursor = mysql.connection.cursor()

        try:
            cursor.execute('''
                SELECT ps.split_id, ps.payment_id, ps.user_id, ps.amount, ps.is_paid, ps.created_at,
                       p.description 
                FROM payment_splits ps
                JOIN payments p ON ps.payment_id = p.payment_id
                WHERE ps.user_id = %s and ps.is_paid = 1
                order by split_id desc
            ''', (user_id,))
            
            transactions = cursor.fetchall()

            if not transactions:
                return jsonify({"message": "No transactions found"}), 404

            # Group transactions by date
            grouped_transactions = defaultdict(list)
            for transaction in transactions:
                date = transaction[5].strftime('%Y-%m-%d')  # Format the date as 'YYYY-MM-DD'
                grouped_transactions[date].append({
                    'split_id': transaction[0],
                    'payment_id': transaction[1],
                    'user_id': transaction[2],
                    'amount': transaction[3],
                    'is_paid': transaction[4],
                    'created_at': transaction[5].strftime('%H:%M'),
                    'description': transaction[6]
                })

            # Convert the defaultdict to a list of dictionaries
            result = {}
            result['data'] = []
            result['message'] = "Succcess"
            for date, trans in grouped_transactions.items():
                total = 0
                for tran in trans:
                    total += tran['amount']
                result['data'].append({
                    'date': date,
                    'amount': total,
                    'transactions': trans
                })

            return jsonify(result), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
    
    def get_total_amount_current_month(self, mysql):
        try:
            current_user_id = get_jwt_identity()

            cursor = mysql.connection.cursor()

            # Calculate the total amount for the current month
            cursor.execute('''
                SELECT SUM(ps.amount) AS total_amount
                FROM payment_splits ps
                JOIN payments p ON ps.payment_id = p.payment_id
                WHERE ps.user_id = %s
                AND MONTH(ps.created_at) = MONTH(CURDATE())
                AND YEAR(ps.created_at) = YEAR(CURDATE())
            ''', (current_user_id,))

            result = cursor.fetchone()
            total_amount = result[0] if result[0] else 0

            return jsonify({"total_amount": total_amount}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            
    def get_home_transactions(self, mysql):
        try:
            current_user_id = get_jwt_identity()

            cursor = mysql.connection.cursor()

            # Get the previous two dates
            cursor.execute('''
                SELECT DISTINCT DATE(ps.created_at) AS transaction_date
                FROM payment_splits ps
                WHERE user_id = %s
                ORDER BY transaction_date DESC
                LIMIT 2
            ''', (current_user_id,))
            date_results = cursor.fetchall()

            if not date_results:
                return jsonify({"message": "No transactions found"}), 404

            dates = [date['transaction_date'] for date in date_results]

            cursor.execute('''
                SELECT 
                    DATE(ps.created_at) AS transaction_date, 
                    ps.split_id, 
                    ps.amount, 
                    ps.is_paid, 
                    p.description 
                FROM 
                    payment_splits ps 
                JOIN 
                    payments p 
                ON 
                    ps.payment_id = p.payment_id 
                WHERE 
                    ps.user_id = %s 
                    AND DATE(ps.created_at) IN (%s, %s)
                ORDER BY 
                    ps.created_at DESC
            ''', (current_user_id, dates[0], dates[1]))

            transactions = cursor.fetchall()

            if not transactions:
                return jsonify({"message": "No transactions found"}), 404

            grouped_transactions = {}
            for transaction in transactions:
                date = transaction['transaction_date']
                if date not in grouped_transactions:
                    grouped_transactions[date] = []
                grouped_transactions[date].append(transaction)

            return jsonify(grouped_transactions), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            
    def get_accounts(self, mysql):
        user_id = get_jwt_identity()
        cursor = mysql.connection.cursor()

        try:
            cursor.execute('''
                WITH discrepancies AS (
                    SELECT
                        ps1.payment_id,
                        ps1.user_id AS user1_id,
                        ps1.amount AS user1_split_amount,
                        ps1.is_paid AS user1_is_paid,
                        ps2.user_id AS user2_id,
                        ps2.amount AS user2_split_amount,
                        ps2.is_paid AS user2_is_paid,
                        u1.user_name AS user1_name,
                        u2.user_name AS user2_name,
                        u2.gender AS gender
                    FROM
                        payment_splits ps1
                    JOIN
                        payment_splits ps2 ON ps1.payment_id = ps2.payment_id
                    JOIN
                        users u1 ON ps1.user_id = u1.user_id
                    JOIN
                        users u2 ON ps2.user_id = u2.user_id
                    WHERE
                        ps1.user_id IN (
                            SELECT DISTINCT user_id FROM payment_splits WHERE payment_id = ps1.payment_id
                        )
                        AND ps2.user_id IN (
                            SELECT DISTINCT user_id FROM payment_splits WHERE payment_id = ps2.payment_id
                        )
                        AND ps1.user_id <> ps2.user_id
                        AND (
                            (ps1.is_paid = 0 AND ps2.is_paid = 1)
                            OR (ps1.is_paid = 1 AND ps2.is_paid = 0)
                        )
                )
                SELECT
                    user1_id AS user_id,
                    user1_name AS user_name,
                    user2_id AS involved_user_id,
                    user2_name AS involved_user_name,
                    gender AS gender,
                    SUM(CASE
                        WHEN user1_is_paid = 0 AND user2_is_paid = 1 THEN -user1_split_amount
                        WHEN user1_is_paid = 1 AND user2_is_paid = 0 THEN user1_split_amount
                        ELSE 0
                    END) AS total_amount
                FROM
                    discrepancies
                WHERE
                    user1_id = %s
                GROUP BY
                    user1_id, user1_name, user2_id, user2_name;
            ''', (user_id,))
            
            transactions = cursor.fetchall()

            if not transactions:
                return jsonify({"message": "No transactions found"}), 404

            column_names = [col[0] for col in cursor.description]
            transation_list = []
            
            for row in transactions:
                transation = dict(zip(column_names, row))
                transation_list.append(transation)

            return jsonify({"data": transation_list}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
    