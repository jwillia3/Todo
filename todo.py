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
import unittest

db = None

def openDatabase(name):
    global db
    db = sqlite3.connect(name)
    db.row_factory = sqlite3.Row
    return db

def rowToHash(row):
    if not row:
        return row
    output = {}
    for i in row.keys():
        output[i] = row[i]
    return output

def addUser(name, email):
    global db
    name = name.decode('utf-8') if type(name) is str else name;
    try:
        c = db.execute("INSERT INTO user VALUES(NULL, ?, ?)", (name, email));
        return { 'id': c.lastrowid }
    except sqlite3.IntegrityError as e:
        return { 'error': 'E-mail already registered' }
def userFromEmail(email):
    global db
    row = db.execute("SELECT * FROM user WHERE email=?", (email,)).fetchone()
    return rowToHash(row) if row else { 'error': email + ' is not registered' }

class Tests(unittest.TestCase):
    def setUp(self):
        global db
        openDatabase(':memory:')
        with open('init.sql') as file:
            script = file.read()
            c = db.cursor()
            c.executescript(script)
            c.close()
        
    def test_addUser(self):
        result = addUser('Demo', 'demo@example.com')
        self.assertEqual(result['id'], 1)
        
        # Duplicate e-mail
        result = addUser('Demo', 'demo@example.com')
        self.assertTrue('error' in result)
        
        # Unicode name
        result = addUser('Démö', 'demo2@example.com')
        self.assertEqual(result['id'], 2)
    
    def test_userFromEmail(self):
        result = addUser('Démö', 'demo@example.com')
        self.assertEqual(result['id'], 1)
        addUser('Obstruction', 'obstruction@example.com')
        
        result = userFromEmail('demo@example.com')
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['name'], u'Démö') # Comes back as Unicode
        self.assertEqual(result['email'], 'demo@example.com')
        
        result = userFromEmail('obstruction@example.com')
        self.assertEqual(result['id'], 2)
        self.assertEqual(result['name'], 'Obstruction')
        self.assertEqual(result['email'], 'obstruction@example.com')
        
        result = userFromEmail('noone@example.com')
        self.assertTrue('error' in result)
        

if __name__ == '__main__':
    unittest.main()
    