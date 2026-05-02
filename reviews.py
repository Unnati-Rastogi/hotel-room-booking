import math
import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "@R00t123",
    "database": "hotel_booking",
    "autocommit": False,
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def insert_reviews(reviews_data):
    """Inserts a list of reviews and auto-determines room_type and view_type from the room_number."""
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        for room_num, name, comment, rating in reviews_data:
            cursor.execute("SELECT room_type, view_type FROM rooms WHERE room_number = %s", (room_num,))
            room = cursor.fetchone()
            rtype = room['room_type'] if room else ''
            vtype = room['view_type'] if room else ''
            
            r_int = int(math.ceil(rating))
            
            cursor.execute("""
                INSERT INTO reviews (customer_name, rating, comment, room_type, view_type, room_number)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, r_int, comment, rtype, vtype, room_num))
            
        conn.commit()
        print(f"Successfully inserted {len(reviews_data)} reviews.")
    except Exception as e:
        print(f"Error inserting reviews: {e}")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def delete_reviews_not_in(names_to_keep):
    """Deletes any reviews where the customer_name is NOT in the provided list."""
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        format_strings = ','.join(['%s'] * len(names_to_keep))
        cursor.execute(f"DELETE FROM reviews WHERE customer_name NOT IN ({format_strings})", tuple(names_to_keep))
        
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"Deleted {deleted_count} old reviews.")
    except Exception as e:
        print(f"Error deleting reviews: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def sync_reviews_with_rooms():
    """Updates reviews with room_type and view_type from the rooms table based on room_number."""
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reviews rev
            JOIN rooms rm ON rev.room_number = rm.room_number
            SET rev.room_type = rm.room_type, rev.view_type = rm.view_type
            WHERE rev.room_number != '' AND rev.room_number IS NOT NULL
        """)
        conn.commit()
        print("Successfully synced review types with rooms table.")
    except Exception as e:
        print(f"Error syncing reviews: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    print("Database review utility script loaded.")
    # Example usage:
    # 
    # reviews_data = [
    #     ("203", "Riya Verma", "Comfortable stay overall.", 3.5),
    #     ("305", "Karan Malhotra", "Really enjoyed the ambience.", 4),
    # ]
    # insert_reviews(reviews_data)
    # 
    # delete_reviews_not_in(["Riya Verma", "Karan Malhotra"])
    # 
    # sync_reviews_with_rooms()
