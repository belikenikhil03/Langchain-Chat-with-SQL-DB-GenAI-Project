import sqlite3
import os

def create_student_database(db_path='student.db'):
    """
    Create and populate the student database if it doesn't exist
    
    Args:
        db_path (str): Path to the SQLite database file
    
    Returns:
        bool: True if database is created/exists, False otherwise
    """
    try:
        # Check if database already exists
        if os.path.exists(db_path):
            print(f"Database {db_path} already exists. Skipping creation.")
            return True

        # Create connection
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Create table with additional columns
        table_info = """
        CREATE TABLE IF NOT EXISTS STUDENT(
            NAME VARCHAR(25), 
            CLASS VARCHAR(25), 
            SECTION VARCHAR(25), 
            MARKS INT,
            AGE INT,
            EMAIL VARCHAR(50),
            ROLL_NUMBER INT
        )
        """
        cursor.execute(table_info)

        # Insert sample data
        student_data = [
            ('Krish', 'Data Science', 'A', 90, 24, 'krish@example.com', 101),
            ('John', 'Data Science', 'B', 100, 22, 'john@example.com', 102),
            ('Mukesh', 'Data Science', 'A', 86, 23, 'mukesh@example.com', 103),
            ('Jacob', 'DevOps', 'A', 50, 25, 'jacob@example.com', 104),
            ('Dipesh', 'DevOps', 'A', 35, 26, 'dipesh@example.com', 105),
            ('Sita', 'AI', 'B', 92, 21, 'sita@example.com', 106),
            ('Rohan', 'Data Science', 'A', 88, 24, 'rohan@example.com', 107),
            ('Alisha', 'AI', 'B', 95, 22, 'alisha@example.com', 108),
            ('Ankit', 'Data Science', 'A', 72, 24, 'ankit@example.com', 109),
            ('Ravi', 'DevOps', 'C', 65, 23, 'ravi@example.com', 110),
            ('Meera', 'AI', 'A', 89, 21, 'meera@example.com', 111),
            ('Aryan', 'Data Science', 'C', 76, 23, 'aryan@example.com', 112),
            ('Tina', 'AI', 'A', 93, 22, 'tina@example.com', 113),
            ('Kiran', 'DevOps', 'B', 55, 26, 'kiran@example.com', 114),
            ('Rahul', 'AI', 'A', 85, 22, 'rahul@example.com', 115),
            ('Priya', 'Data Science', 'B', 91, 24, 'priya@example.com', 116),
            ('Amit', 'DevOps', 'C', 60, 25, 'amit@example.com', 117),
            ('Neha', 'Data Science', 'A', 87, 21, 'neha@example.com', 118),
            ('Sameer', 'AI', 'B', 74, 22, 'sameer@example.com', 119),
            ('Raj', 'DevOps', 'A', 40, 26, 'raj@example.com', 120),
            ('Nisha', 'Data Science', 'C', 92, 24, 'nisha@example.com', 121),
            ('Vikas', 'AI', 'A', 81, 22, 'vikas@example.com', 122),
            ('Divya', 'DevOps', 'B', 68, 25, 'divya@example.com', 123),
            ('Harsha', 'Data Science', 'A', 85, 23, 'harsha@example.com', 124),
            ('Pooja', 'AI', 'C', 90, 21, 'pooja@example.com', 125)
        ]

        # Use parameterized query for better security
        cursor.executemany(
            'INSERT INTO STUDENT (NAME, CLASS, SECTION, MARKS, AGE, EMAIL, ROLL_NUMBER) VALUES (?, ?, ?, ?, ?, ?, ?)', 
            student_data
        )

        # Commit and close
        connection.commit()
        connection.close()

        print("Student database created and populated successfully.")
        return True

    except sqlite3.Error as e:
        print(f"Error creating database: {e}")
        return False

def verify_database_contents(db_path='student.db'):
    """
    Verify the contents of the student database
    
    Args:
        db_path (str): Path to the SQLite database file
    
    Returns:
        list: List of tuples containing student records
    """
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Fetch all records
        cursor.execute('SELECT * FROM STUDENT')
        records = cursor.fetchall()

        # Print records
        print("Inserted Records:")
        for row in records:
            print(row)

        connection.close()
        return records

    except sqlite3.Error as e:
        print(f"Error accessing database: {e}")
        return []

# Run database creation and verification
if __name__ == "__main__":
    create_student_database()
    verify_database_contents()
