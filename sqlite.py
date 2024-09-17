import sqlite3

connection = sqlite3.connect("student.db")

cursor = connection.cursor()

table_info = """
create table STUDENT(NAME VARCHAR(25), CLASS VARCHAR(25), SECTION VARCHAR(25), MARKS INT)
"""

cursor.execute(table_info)

cursor.execute('''Insert into STUDENT values('Krish', 'Data Science', 'A', 90)''')
cursor.execute('''Insert into STUDENT values('John', 'Data Science', 'B', 100)''')
cursor.execute('''Insert into STUDENT values('Mukesh', 'Data Science', 'A', 86)''')
cursor.execute('''Insert into STUDENT values('Jacob', 'Devops', 'A', 50)''')
cursor.execute('''Insert into STUDENT values('Dipesh', 'Devops', 'A', 35)''')

print("The inserted records are")
data = cursor.execute('''Select * from STUDENT''')
for row in data:
    print(row)

connection.commit()
connection.close()