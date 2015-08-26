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
import datetime

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
def addItem(user, due, title):
    global db
    c = db.execute("INSERT INTO item VALUES(NULL, ?, ?, ?, CURRENT_TIMESTAMP, 0)",
        (user, due, title))
    return { 'id': c.lastrowid }
def getUserItems(user, done=None):
    global db
    sql = "SELECT * FROM item WHERE userid=?"
    if done != None:
        sql += ' AND done = ' + ('1' if done else '0')
    rows = db.execute(sql, (user, )).fetchall()
    return [rowToHash(row) for row in rows]
def completeItem(id, done=True):
    global db
    c = db.execute("UPDATE item SET done = "  + ('1' if done else '0') + " WHERE id=?", (id,))
    return { } if c.rowcount == 1 else { 'error': 'Item does not exist' }

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
    
    def test_addItem(self):
        result = addUser('Démö', 'demo@example.com')
        userid = result['id']
        
        result = addItem(userid, datetime.datetime.utcnow(), 'One')
        self.assertEqual(result, { 'id': 1 })
        result = addItem(userid, datetime.datetime.utcnow(), 'Two')
        self.assertEqual(result, { 'id': 2 })
        result = addItem(userid, datetime.datetime.utcnow(), 'Two')
        self.assertEqual(result, { 'id': 3 })
    
    def test_completeItem(self):
        result = addUser('Démö', 'demo@example.com')
        userid = result['id']
        
        result = addItem(userid, datetime.datetime.utcnow(), 'One')
        self.assertEqual(result, { 'id': 1 })
        
        result = completeItem(1)
        self.assertEqual(result, { })
        
        result = completeItem(2)
        self.assertTrue('error' in result)
        
    
    def test_getUserItems(self):
        def orderById(a, b):
            return cmp(a['id'], b['id'])
            
        result = addUser('Démö', 'demo@example.com')
        userid = result['id']
        
        date1 = datetime.datetime.utcnow()
        addItem(userid, date1, 'One')
        
        date2 = datetime.datetime.utcnow()
        addItem(userid, date1, 'Two')
        
        date3 = datetime.datetime.utcnow()
        addItem(userid, date1, 'Three')
        
        # Make sure that all are returned if completion is not an issue
        result = getUserItems(userid)
        result.sort(orderById)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], { 'id': 1, 'userid': userid, 'due': str(date1), 'title': 'One', 'created': result[0]['created'], 'done': 0 })
        self.assertEqual(result[1], { 'id': 2, 'userid': userid, 'due': str(date2), 'title': 'Two', 'created': result[1]['created'], 'done': 0 })
        self.assertEqual(result[2], { 'id': 3, 'userid': userid, 'due': str(date3), 'title': 'Three', 'created': result[2]['created'], 'done': 0 })
        
        # Complete a task
        result = completeItem(2)
        self.assertEqual(result, { })
        
        # Get complete
        result = getUserItems(userid, True)
        result.sort(orderById)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], { 'id': 2, 'userid': userid, 'due': str(date2), 'title': 'Two', 'created': result[0]['created'], 'done': 1 })
        
        # Get incomplete
        result = getUserItems(userid, False)
        result.sort(orderById)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], { 'id': 1, 'userid': userid, 'due': str(date1), 'title': 'One', 'created': result[0]['created'], 'done': 0 })
        self.assertEqual(result[1], { 'id': 3, 'userid': userid, 'due': str(date3), 'title': 'Three', 'created': result[1]['created'], 'done': 0 })
        
        # Get all again
        result = getUserItems(userid)
        result.sort(orderById)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], { 'id': 1, 'userid': userid, 'due': str(date1), 'title': 'One', 'created': result[0]['created'], 'done': 0 })
        self.assertEqual(result[1], { 'id': 2, 'userid': userid, 'due': str(date2), 'title': 'Two', 'created': result[1]['created'], 'done': 1 })
        self.assertEqual(result[2], { 'id': 3, 'userid': userid, 'due': str(date3), 'title': 'Three', 'created': result[2]['created'], 'done': 0 })
        
        # Incomplete a task
        result = completeItem(2, False)
        self.assertEqual(result, { })
        
        # Make sure task was incompleted
        result = getUserItems(userid)
        result.sort(orderById)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], { 'id': 1, 'userid': userid, 'due': str(date1), 'title': 'One', 'created': result[0]['created'], 'done': 0 })
        self.assertEqual(result[1], { 'id': 2, 'userid': userid, 'due': str(date2), 'title': 'Two', 'created': result[1]['created'], 'done': 0 })
        self.assertEqual(result[2], { 'id': 3, 'userid': userid, 'due': str(date3), 'title': 'Three', 'created': result[2]['created'], 'done': 0 })
        

if __name__ == '__main__':
    unittest.main()
    