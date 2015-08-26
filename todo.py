#!/bin/env python
# vim: encoding=utf8
# • Through the web service’s API, we need to be able to
#   o   Create a new todo item for a given user with a due date
#   o   Mark a todo item as complete
#   o   Retrieve the todo items for a given user
#   o   Retrieve the incomplete todo items for a given user
# • All data must be persisted in some manner
# • Both requests and responses must be represented as JSON
# • Neither authentication nor authorization are required
import sqlite3
db = None
def openDatabase(name):
    db = sqlite3.connect(name)
    db.row_factory = sqlite3.Row
    return db

def rowToHash(row):
    output = {}
    for i in row.keys():
        output[i] = row[i]
    return output


def runTests():
    global db
    try:
        db = openDatabase(':memory:')
        with open('init.sql') as file:
            script = file.read()
            c = db.cursor()
            c.executescript(script)
            c.close()
        
        for row in db.execute("SELECT * FROM sqlite_master WHERE type='table'"):
            row = rowToHash(row)
            print(row['sql'])
    finally:
        db.close()
        
if __name__ == '__main__':
    runTests()
    