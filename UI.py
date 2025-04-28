from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
from werkzeug.security import check_password_hash
from hashlib import sha256

#Globals
listy = ['any', 'arb', 'hundred', 'true', 'bny', 'cny']
category_dictionary = {'Any%':[102, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 92, 48, 49, 50, 51, 18, 19, 20, 21, 22, 26, 27, 28, 29, 30, 31, 32, 33],
                        'ARB':[102, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 23, 25, 27, 28, 29, 30, 31, 32, 33, 93, 95, 97, 99, 62, 53, 54, 55, 71, 72, 73, 74], 
                        '100%':[1, 2, 3, 4, 5, 6, 7, 8, 9, 10,11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30,31, 32, 33, 34, 35, 36, 37, 38, 39, 40,41, 42, 43, 44, 45, 46, 47, 48, 49, 50,51, 52, 53, 54, 55, 56, 57, 58, 59, 60,61, 62, 63, 64, 65, 66, 67, 68, 69, 70,71, 72, 73, 74, 75, 76, 77, 78, 79, 80,81, 82, 83, 84, 85, 86, 87, 88, 89, 90,91, 92, 93, 94, 95, 96, 97, 98, 99, 100,101, 102, 103], 
                        'True Ending': [102,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,92,48,49,50,51,18,19,93,52,53,54,55,27,28,29,30,31,32,33,99,71,72,73,74,79,80,81,82,83,84,85,86,87], 
                        'Bny%': [102,1,88,34,35,36,89,37,38,39,7,8,90,40,41,42,43,11,91,44,45,46,47,15,92,48,49,50,51,18,19,93,52,53,54,55,27,28,29,94,56,57,58,59,60,61,62], 
                        'Cny%': [103,63,64,65,66,67,68,69,70]}



with sqlite3.connect("times.db",check_same_thread=False) as database: #Connecting the database
    db=database.cursor()
    app=Flask(__name__)
    app.secret_key = 'password'
    

    def new_user_data(id, username, category):
        for checkpoint in category_dictionary[category]:
            print(checkpoint)
            db.execute('SELECT name FROM Checkpoint WHERE id = ?', (checkpoint,))
            results = db.fetchone()
            name = results[0]
            print(name)
            chapter_name = (name.split(' '))[-1]
            print(chapter_name)
            db.execute('SELECT id FROM Chapter WHERE name == ?', (chapter_name,))
            results = db.fetchone()
            chapter_id = results[0]
            db.execute('SELECT id FROM Category WHERE name == ?', (category,))
            results = db.fetchone()
            category_id = results[0]
            db.execute('INSERT INTO Run (run_number, type, chapter_id, user_id, category_id) VALUES (?, ?, ?, ?, ?)', (checkpoint, 'checkpoint', chapter_id, id, category_id))
        database.commit()


    @app.route('/')
    def home():
        return render_template('home.html', title='Home')
    
    @app.route('/signup')
    def signup():
        return render_template('signup.html')
    
    @app.route('/new_user', methods=['POST'])
    def new_user():
        username = request.form.get('username')
        password = request.form.get('password')
       
        h = sha256()
        h.update(password.encode())
        hash = h.hexdigest()
        db.execute('INSERT INTO User (name, hash) VALUES (?, ?)', (username, hash))
        #Any%
        database.commit()
        db.execute('SELECT id FROM User WHERE name == ?', (username,))
        results = db.fetchone()
        id = results[0]
        print(id)
        for category in category_dictionary:
            new_user_data(id, username, category)
        return render_template('home.html')
    
    @app.route('/search', methods=['POST'])
    def search():
        username = request.form.get('username')
        password = request.form.get('password')

        db.execute(f'SELECT id, hash FROM User WHERE name = "{username}";')
        results=db.fetchone()
        if results:
            h = sha256()
            h.update(password.encode())
            hashed = h.hexdigest()
            user_id, hash = results
            if hash == hashed:
           
            
                return redirect(url_for('get_times',user_id=user_id, category_id=1))

            return render_template('profile.html', user_id = user_id, category_id = 1)
        
        print('No user found.')
        return render_template('home.html')

    @app.route('/get_times/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def get_times(user_id,category_id):
        data_dictionary = {}
        checkpoints = []
        db.execute('SELECT time, run_number FROM Run WHERE user_id = ? AND category_id = ?', (user_id, category_id))
        results = db.fetchall()

        times = [i[0] for i in results]
        checkpoint_id = [j[1] for j in results]
        for checkpoint in checkpoint_id:
            db.execute('SELECT name FROM Chapter WHERE id IN (SELECT chapter_id FROM Run WHERE run_number = ? AND user_id = ? AND category_id = ?);', (checkpoint, user_id, category_id))
            results = db.fetchone()
            print(results)
            
            data_dictionary[results[0]] = []
            

            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,))
            checkpoint_name = db.fetchone()
            data_dictionary[results[0]].append(checkpoint_name[0])
                
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name, count = db.fetchall()[0]
        print(data_dictionary)

       
        print(times, checkpoint_id, checkpoints, name)
        return render_template('get_times.html', user_id = user_id, category_id = category_id, times = times, checkpoints = checkpoints, count = count, name = name)

    
    @app.route('/update_times/<int:user_id>/<int:category_id>', methods=['POST'])
    def update_times(user_id,category_id):
         
        if request.method == 'POST':
            checkpoint_times=request.form.getlist('checkpoints[]')
        #get the times from the url
        #update the database
        return render_template('profile.html',user_id=user_id,category_id=category_id)
    
    @app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def profile(user_id, category_id):
        checkpoints = []
        db.execute('SELECT time, run_number FROM Run WHERE id = ? AND category_id = ?', (user_id, category_id))
        times = [row[0] for row in db.fetchall()]
        checkpoint_id = [row[1] for row in db.fetchall()]
        for checkpoint in checkpoint_id:
            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,))
            checkpoints.append(db.fetchall())
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name, count = db.fetchall()
        return render_template('profile.html', user_id = user_id, category_id = category_id, times = times, checkpoints = checkpoints, count = count, name = name)

if __name__ == '__main__':
    app.run(debug=True)