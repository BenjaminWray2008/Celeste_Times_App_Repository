from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
from werkzeug.security import check_password_hash
from hashlib import sha256

#Globals
listy = ['hi', 'Any%', 'ARB', '100%', 'True Ending', 'Bny%', 'Cny%']


with sqlite3.connect("times.db",check_same_thread=False) as database: #Connecting the database
    db=database.cursor()
    app=Flask(__name__)
    app.secret_key = 'password'
    

    def new_user_data(id):
        db.execute('SELECT id FROM Category;')
        results = db.fetchall()
        for category in results:
            category_id = category[0]
            db.execute('SELECT checkpoint_id FROM CategoryCheckpoint WHERE category_id = ?', (category_id,))
            checkpoints_list = db.fetchall()
            for checkpoint in checkpoints_list:
                print(checkpoint)
                db.execute('SELECT name FROM Checkpoint WHERE id = ?', (checkpoint[0],))
                results = db.fetchone()
                name = results[0]
                print(name)
                chapter_name = (name.split(' '))[-1]
                print(chapter_name)
                db.execute('SELECT id FROM Chapter WHERE name == ?', (chapter_name,))
                results = db.fetchone()
                chapter_id = results[0]
                db.execute('INSERT INTO Run (run_number, type, chapter_id, user_id, category_id) VALUES (?, ?, ?, ?, ?)', (checkpoint[0], 'checkpoint', chapter_id, id, category_id))
        database.commit()

    def data_dictionary_creation(user_id, category_id):
        data_dictionary = {}
        db.execute('SELECT time, run_number FROM Run WHERE user_id = ? AND category_id = ?', (user_id, category_id))
        results = db.fetchall()
        checkpoint_id = [j[1] for j in results]
        print(checkpoint_id)
        for checkpoint in checkpoint_id:
            db.execute('SELECT name FROM Chapter WHERE id IN (SELECT chapter_id FROM Run WHERE run_number = ? AND user_id = ? AND category_id = ?);', (checkpoint, user_id, category_id))
            results = db.fetchone()
            print(results)
            if results[0] not in data_dictionary:
                data_dictionary[results[0]] = []
            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,))
            checkpoint_name = db.fetchone()
            db.execute('SELECT time FROM Run WHERE user_id = ? AND category_id = ? AND run_number = ?;', (user_id, category_id, checkpoint))
            time = db.fetchone()
            
            data_dictionary[results[0]].append((' '.join(checkpoint_name[0].split(' ')[:-1]), time[0]))
        return data_dictionary


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
      
        new_user_data(id)
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
        data_dictionary = data_dictionary_creation(user_id, category_id)
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
        for i in data_dictionary:
            print(i)
        return render_template('get_times.html', user_id = user_id, category_id = category_id, data_dictionary = data_dictionary, name = name)

    
    @app.route('/update_times/<int:user_id>/<int:category_id>', methods=['POST'])
    def update_times(user_id,category_id):
         
        if request.method == 'POST':
            checkpoint_times=request.form.getlist('checkpoints[]')
            print(checkpoint_times)



            data_dictionary = data_dictionary_creation(user_id, category_id)
        
            list_of_checkpoints = []
            for chapter in data_dictionary:
                for checkpoint_tuple in data_dictionary[chapter]:
                    print(checkpoint_tuple[0])
                    list_of_checkpoints.append(checkpoint_tuple[0])

            for time, checkpoint in zip(checkpoint_times, list_of_checkpoints):
                if time != '':
                    print('HI')
                    print(checkpoint, time)
                    db.execute('SELECT id FROM Checkpoint WHERE name = ?', (checkpoint,))
                    results = db.fetchone()
                    checkpoint_id = results[0]
                    db.execute('UPDATE Run SET time = ? WHERE user_id = ? AND category_id = ? AND run_number = ?;', (time, user_id, category_id, checkpoint_id))
                    database.commit()
        
        return redirect(url_for('profile',user_id=user_id,category_id=category_id))
    
    @app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def profile(user_id, category_id):
        data_dictionary = data_dictionary_creation(user_id, category_id)
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
       
        return render_template('profile.html', user_id = user_id, category_id = category_id, data_dictionary = data_dictionary, name = name)

if __name__ == '__main__':
    app.run(debug=True)