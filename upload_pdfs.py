import os
import mysql.connector
from mysql.connector import Error

# Configuration
PDF_FOLDER = r'C:\Users\akshi\Desktop\folder with pdfs'
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Akshita@2003',
    'database': 'login_credentials_drdoapp'
}


def connect_to_database():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None


def upload_pdfs(connection):
    cursor = connection.cursor()
    sql = "INSERT INTO pdf_files (file_name, file_data) VALUES (%s, %s)"

    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith('.pdf'):
            file_path = os.path.join(PDF_FOLDER, filename)
            with open(file_path, 'rb') as file:
                binary_data = file.read()
                try:
                    cursor.execute(sql, (filename, binary_data))
                except Error as e:
                    print(f"Failed to insert {filename}: {e}")

            # Commit the transaction periodically to avoid losing data in case of failure
            connection.commit()

    connection.commit()
    cursor.close()


if __name__ == "__main__":
    conn = connect_to_database()
    if conn:
        upload_pdfs(conn)
        conn.close()

