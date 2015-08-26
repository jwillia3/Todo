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
import os
import json
import urlparse

db = None
cwd = os.path.dirname(os.path.realpath(__file__))
actionWhitelist = ('addUser', 'getUserFromEmail', 'addItem', 'getUserItems', 'completeItem')

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
    if not name:
        return { 'error': 'Name cannot be blank' }
    if '@' not in email:
        return { 'error': 'Not a valid e-mail address' }
    
    try:
        c = db.execute("INSERT INTO user VALUES(NULL, ?, ?)", (name, email));
        db.commit()
        return { 'id': c.lastrowid }
    except sqlite3.IntegrityError as e:
        return { 'error': 'E-mail already registered' }
def getUserFromEmail(email):
    global db
    if not email:
        return { 'error': 'E-mail cannot be blank' }
    row = db.execute("SELECT * FROM user WHERE email=?", (email,)).fetchone()
    return rowToHash(row) if row else { 'error': email + ' is not registered' }
def addItem(user, due, title):
    global db
    if not user:
        return { 'error': 'User cannot be blank' }
    if not due:
        return { 'error': 'Due date cannot be blank' }
    if not title:
        return { 'error': 'Title cannot be blank' }
    c = db.execute("INSERT INTO item VALUES(NULL, ?, ?, ?, CURRENT_TIMESTAMP, 0)",
        (user, due, title))
    db.commit()
    return { 'id': c.lastrowid }
def getUserItems(user, done=None):
    global db
    if not user:
        return { 'error': 'User cannot be blank' }
    sql = "SELECT * FROM item WHERE userid=?"
    if done != None:
        sql += ' AND done = ' + ('1' if done else '0')
    rows = db.execute(sql, (user, )).fetchall()
    return [rowToHash(row) for row in rows]
def completeItem(id, done=True):
    global db
    if not id:
        return { 'error': 'ID cannot be blank' }
    c = db.execute("UPDATE item SET done = "  + ('1' if done else '0') + " WHERE id=?", (id,))
    db.commit()
    return { 'id': id } if c.rowcount == 1 else { 'error': 'Item does not exist' }

def dispatch(request):
    global actionWhitelist
    if request['action'] not in actionWhitelist:
        return { 'error': 'Action is not supported' }
    
    func = globals()[request['action']]
    del request['action']
    params = set(func.func_code.co_varnames[:func.func_code.co_argcount])
    if params != set(request.keys()):
        return { 'error': 'Missing or extra arguments' }
    
    return func(**request)


class Tests(unittest.TestCase):
    def setUp(self):
        global db
        openDatabase(':memory:')
        with open('init.sql') as file:
            script = file.read()
            c = db.cursor()
            c.executescript(script)
            db.commit()
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
        
        # No name
        result = addUser('', 'demo@example.com')
        self.assertTrue('error' in result)
        
        # Bad e-mail
        result = addUser('Demo', 'demoexample.com')
        self.assertTrue('error' in result)
    
    def test_getUserFromEmail(self):
        result = addUser('Démö', 'demo@example.com')
        self.assertEqual(result['id'], 1)
        addUser('Obstruction', 'obstruction@example.com')
        
        result = getUserFromEmail('demo@example.com')
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['name'], u'Démö') # Comes back as Unicode
        self.assertEqual(result['email'], 'demo@example.com')
        
        result = getUserFromEmail('obstruction@example.com')
        self.assertEqual(result['id'], 2)
        self.assertEqual(result['name'], 'Obstruction')
        self.assertEqual(result['email'], 'obstruction@example.com')
        
        result = getUserFromEmail('noone@example.com')
        self.assertTrue('error' in result)
        
        self.assertTrue('error' in getUserFromEmail(None))
    
    def test_addItem(self):
        result = addUser('Démö', 'demo@example.com')
        userid = result['id']
        
        result = addItem(userid, datetime.datetime.utcnow(), 'One')
        self.assertEqual(result, { 'id': 1 })
        result = addItem(userid, datetime.datetime.utcnow(), 'Two')
        self.assertEqual(result, { 'id': 2 })
        result = addItem(userid, datetime.datetime.utcnow(), 'Two')
        self.assertEqual(result, { 'id': 3 })
        
        # Bad input
        self.assertTrue('error' in addItem(None, datetime.datetime.utcnow(), 'Example'))
        self.assertTrue('error' in addItem(userid, None, 'Example'))
        self.assertTrue('error' in addItem(userid, datetime.datetime.utcnow(), None))
    
    def test_completeItem(self):
        result = addUser('Démö', 'demo@example.com')
        userid = result['id']
        
        result = addItem(userid, datetime.datetime.utcnow(), 'One')
        self.assertEqual(result, { 'id': 1 })
        
        result = completeItem(1)
        self.assertEqual(result, { 'id': 1 })
        
        result = completeItem(2)
        self.assertTrue('error' in result)
        
        self.assertTrue('error' in completeItem(None))
        
    
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
        self.assertEqual(result, { 'id': 2 })
        
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
        self.assertEqual(result, { 'id': 2 })
        
        # Make sure task was incompleted
        result = getUserItems(userid)
        result.sort(orderById)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], { 'id': 1, 'userid': userid, 'due': str(date1), 'title': 'One', 'created': result[0]['created'], 'done': 0 })
        self.assertEqual(result[1], { 'id': 2, 'userid': userid, 'due': str(date2), 'title': 'Two', 'created': result[1]['created'], 'done': 0 })
        self.assertEqual(result[2], { 'id': 3, 'userid': userid, 'due': str(date3), 'title': 'Three', 'created': result[2]['created'], 'done': 0 })
        
        self.assertTrue('error' in getUserItems(None))
    
    def test_dispatch(self):
        result = dispatch({ 'action': 'addUser', 'email': 'demo@example.com', 'name': 'Démö' })
        self.assertEqual(result['id'], 1)
        
        # Missing arg
        result = dispatch({ 'action': 'addUser', 'email': 'demo3@example.com' })
        self.assertTrue('error' in result)
        
        # Too many args
        result = dispatch({ 'action': 'addUser', 'email': 'demo4@example.com', 'name': 'Démö', 'bad': None })
        self.assertTrue('error' in result)
        
        # Non-whitelisted action
        self.assertTrue('id' not in dispatch({ 'action': 'openDatabase', 'name': ':memory:' }))
        
        # Test dispatch of all whitelisted
        self.assertTrue('id' in dispatch({ 'action': 'addUser', 'email': 'demo2@example.com', 'name': 'Démöstætion' }))
        self.assertTrue('id' in dispatch({ 'action': 'getUserFromEmail', 'email': 'demo@example.com' }))
        self.assertTrue('id' in dispatch({ 'action': 'addItem', 'user': 1, 'title': 'One', 'due': datetime.datetime.utcnow() }))
        self.assertTrue('id' in dispatch({ 'action': 'addItem', 'user': 1, 'title': 'Two', 'due': datetime.datetime.utcnow() }))
        self.assertTrue('id' in dispatch({ 'action': 'addItem', 'user': 1, 'title': 'Three', 'due': datetime.datetime.utcnow() }))
        self.assertEqual(3, len(dispatch({ 'action': 'getUserItems', 'user': 1, 'done': None })))
        self.assertTrue('id' in dispatch({ 'action': 'completeItem', 'id': 2, 'done': True }))

def application(environ, start_response):
    status = '200 OK'
    output = ''
    
    request = urlparse.parse_qs(environ['QUERY_STRING'])
    request = request['json'][0] if 'json' in request else None
    try:
        request = json.loads(request) if request else None
    except ValueError:
        request = None
        
    if request:
        global db
        try:
            openDatabase(os.path.join(cwd, 'todo.db'))
            output = dispatch(request)
        except sqlite3.OperationalError as e:
            print(e)
            output = { 'error': 'Database error' }
        finally:
            if db:
                db.close()
    else:
        output = { 'error': 'Invalid JSON' }
    
    if type(output) is not str:
        output = json.dumps(output)
    start_response(status, [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(output))),
        ])
    return output
    

if __name__ == '__main__':
    unittest.main()