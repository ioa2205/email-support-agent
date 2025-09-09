import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# --- Use environment variables for database connection ---
DB_NAME = os.getenv("DB_NAME", "email_agent")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mysecretpassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    return conn

def setup_database():
    """Create all necessary tables if they don't exist."""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS connected_accounts (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            token_expiry TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR(50) PRIMARY KEY,
            customer_email VARCHAR(255) NOT NULL,
            order_date DATE NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status VARCHAR(50) DEFAULT 'completed'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS unhandled_emails (
            id SERIAL PRIMARY KEY,
            received_from VARCHAR(255) NOT NULL,
            subject TEXT,
            body TEXT,
            category VARCHAR(50),
            importance SMALLINT CHECK (importance >= 1 AND importance <= 5),
            received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            status VARCHAR(50) DEFAULT 'pending'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS not_found_refund_requests (
            id SERIAL PRIMARY KEY,
            customer_email VARCHAR(255) NOT NULL,
            invalid_order_id_attempted VARCHAR(255),
            full_email_body TEXT,
            logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    )
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        
        # Add sample orders
        cur.execute("SELECT COUNT(*) FROM orders;")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO orders (order_id, customer_email, order_date, amount, status) VALUES (%s, %s, %s, %s, %s)",
                ('ORD12345', 'sender-email@example.com', '2023-10-01', 99.99, 'completed')
            )
            cur.execute(
                "INSERT INTO orders (order_id, customer_email, order_date, amount, status) VALUES (%s, %s, %s, %s, %s)",
                ('ORD67890', 'another-sender@example.com', '2023-10-15', 45.50, 'completed')
            )
        
        cur.close()
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    print("Setting up database...")
    setup_database()
    print("Database setup complete.")