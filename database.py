# database.py
import sqlite3
from datetime import datetime
from config import DATABASE_NAME

def init_db():
    """Initialize the database with proper schema"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 package TEXT NOT NULL,
                 coin_details TEXT NOT NULL,
                 status TEXT DEFAULT 'pending',
                 website_id TEXT,
                 website_link TEXT,
                 sol_amount REAL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_order(user_id, package, details, sol_amount, status="pending"):
    """Save a new order with all required fields"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO orders 
                (user_id, package, coin_details, sol_amount, status)
                VALUES (?, ?, ?, ?, ?)''', 
             (user_id, package, details, sol_amount, status))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_order(order_id):
    """Get complete order details"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = c.fetchone()
    conn.close()
    
    if order:
        return {
            'id': order[0],
            'user_id': order[1],
            'package': order[2],
            'coin_details': order[3],
            'status': order[4],
            'website_id': order[5],
            'website_link': order[6],  # Add this line
            'sol_amount': order[7],
            'created_at': order[8]
        }
    return None

def update_order_status(order_id, status, website_id=None):
    """Update order status and website ID"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    if website_id:
        c.execute('''UPDATE orders 
                   SET status = ?, website_id = ?
                   WHERE id = ?''', 
                 (status, website_id, order_id))
    else:
        c.execute('''UPDATE orders 
                   SET status = ?
                   WHERE id = ?''', 
                 (status, order_id))
    conn.commit()
    conn.close()

def get_order_by_id(order_id):
    print(order_id)
    """Get order by ID with proper error handling"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''SELECT * FROM orders WHERE id = ?''', (order_id,))
    order = c.fetchone()
    conn.close()
    
    if order:
        return {
            'id': order[0],
            'user_id': order[1],
            'package': order[2],
            'coin_details': order[3],
            'status': order[4],
            'website_id': order[5],
            'website_link': order[6], 
            'sol_amount': order[7],
            'created_at': order[8]
        }
    return None

def get_all_pending_orders():
    """Get all pending orders with proper formatting"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC''')
    orders = []
    for order in c.fetchall():
        orders.append({
            'id': order[0],
            'user_id': order[1],
            'package': order[2],
            'coin_details': order[3],
            'status': order[4],
            'created_at': order[7]
        })
    conn.close()
    return orders


def complete_order(order_id: int, website_url: str) -> bool:
    """Mark an order as completed with website URL"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        # Update both status and website_link
        c.execute('''UPDATE orders 
                    SET status = 'completed', 
                        website_link = ?
                    WHERE id = ?''', 
                 (website_url, order_id))
        conn.commit()
        return c.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def get_user_id_by_order_id(order_id: int) -> int:
    """Get user ID associated with a specific order"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        result = c.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()