from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
from werkzeug.security import check_password_hash
from hashlib import sha256
import re
from math import trunc

#Globals
listy = ['hi', 'Any%', 'ARB', '100%', 'True Ending', 'Bny%', 'Cny%']
another_listy = [0.001, 1, 60, 3600]

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
                db.execute('INSERT INTO Run (time, run_number, type, chapter_id, user_id, category_id) VALUES (0, ?, ?, ?, ?, ?)', (checkpoint[0], 'checkpoint', chapter_id, id, category_id))
        database.commit()

    def data_dictionary_creation(user_id, category_id, variable):
        data_dictionary = {}
        db.execute('SELECT checkpoint_id, orderer FROM CategoryCheckpoint WHERE category_id = ? ORDER BY orderer ASC', (category_id,))
        results = db.fetchall()
        checkpoint_id = [j[0] for j in results]
        
        for checkpoint in checkpoint_id:
            db.execute('SELECT name FROM Chapter WHERE id IN (SELECT chapter_id FROM Run WHERE run_number = ? AND user_id = ? AND category_id = ?);', (checkpoint, user_id, category_id))
            results = db.fetchone()
           
            if results[0] not in data_dictionary:
                data_dictionary[results[0]] = []
            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,))
            checkpoint_name = db.fetchone()
            db.execute('SELECT time FROM Run WHERE user_id = ? AND category_id = ? AND run_number = ?;', (user_id, category_id, checkpoint))
            time = db.fetchone()
            data_dictionary[results[0]].append((checkpoint_name[0], time[0]))
    #   if variable:
    #             data_dictionary[results[0]].append((checkpoint_name[0], time[0]))
    #         else:
    #             data_dictionary[results[0]].append((' '.join(checkpoint_name[0].split(' ')[:-1]), time[0]))
        if variable:
            
            for chapter in data_dictionary:
                total = 0
                for time_tuple in data_dictionary[chapter]:
                    total_individual_time = 0
               
                    if time_tuple[1] is not None:
                        print(time_tuple[1])
                        time_list = re.split('[.:]', time_tuple[1])
                        backwards_time_list = reversed(time_list)
                        for index, time_segment in enumerate(backwards_time_list):
                            total_individual_time += (float(time_segment)*float(another_listy[index]))

                        total += round(total_individual_time,3)
                if total != None and total != 0:
                    print(total)
                    total_list = str(round(total,3)).split('.')
                    print(total_list)
                    ms = total_list[1]
                    if len(ms) != 3:
                        length = len(ms)
                        ms += f'{str(0)*(3-length)}'
                    m_s = str((float(total_list[0])/60)).split('.')
                    m = m_s[0]
                    s = trunc(float(total_list[0])-(int(m)*60))   
                    if len(str(s)) != 2:
                        length = len(str(s))
                        s = str(s)
                        s += f'{str(0)*(2-length)}'
                    print(ms, m, s)
                    final_time = f'{m}:{s}.{ms}'
                else:
                    final_time = 0
                data_dictionary[chapter].append(('Total Total', final_time))
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
        data_dictionary = data_dictionary_creation(user_id, category_id, False)
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
     
        return render_template('get_times.html', user_id = user_id, category_id = category_id, data_dictionary = data_dictionary, name = name)

    
    @app.route('/update_times/<int:user_id>/<int:category_id>', methods=['POST'])
    def update_times(user_id,category_id):
         
        if request.method == 'POST':
            checkpoint_times=request.form.getlist('checkpoints[]')
            print(checkpoint_times)



            data_dictionary = data_dictionary_creation(user_id, category_id, False)
        
            list_of_checkpoints = []
            print(data_dictionary)
            for chapter in data_dictionary:
                
                for checkpoint_tuple in data_dictionary[chapter]:
                 
                    if checkpoint_tuple[0] != 'Total Total':
                        list_of_checkpoints.append(checkpoint_tuple[0])
  
            for time, checkpoint in zip(checkpoint_times, list_of_checkpoints):
                if time != '':
                    for char in time:
                        if char in '0123456789.:':
                 
                            db.execute('SELECT id FROM Checkpoint WHERE name = ?', (checkpoint,))
                            results = db.fetchone()
                            checkpoint_id = results[0]
                            db.execute('UPDATE Run SET time = ? WHERE user_id = ? AND category_id = ? AND run_number = ?;', (time, user_id, category_id, checkpoint_id))
                            database.commit()
                    
        
        return redirect(url_for('profile',user_id=user_id,category_id=category_id))
    
    @app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def profile(user_id, category_id):
        data_dictionary = data_dictionary_creation(user_id, category_id, True)
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
        db.execute('SELECT name FROM user WHERE id = ?', (user_id,))
        user_name = db.fetchall()[0]
        return render_template('profile.html', user_id = user_id, category_id = category_id, data_dictionary = data_dictionary, name = name, user_name = user_name)

if __name__ == '__main__':
    app.run(debug=True)