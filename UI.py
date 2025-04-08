from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
from werkzeug.security import check_password_hash
from hashlib import sha256

#Globals
any = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 92, 48, 49, 50, 51, 18, 19, 20, 21, 22, 26, 27, 28, 29, 30, 31, 32, 33]
arb = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 27, 28, 29, 30, 31, 32, 33, 93, 95, 97, 99, 62, 53, 54, 55, 71, 72, 73, 74]
hundred = [i for i in range(102)]
true = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 27, 28, 29, 30, 31, 32, 33, 71, 72, 73, 74, 95, 97, 99, 52, 53, 54, 55]
bny = []

with sqlite3.connect("times.db",check_same_thread=False) as database: #Connecting the database
    db=database.cursor()
    app=Flask(__name__)
    app.secret_key = 'password'

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

        db.execute('INSERT INTO Runs ()')
        database.commit()
        
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
        checkpoints = []
        db.execute('SELECT time, run_number FROM Run WHERE id = ? AND category_id = ?', (user_id, category_id))
        times = [row[0] for row in db.fetchall()]
        checkpoint_id = [row[1] for row in db.fetchall()]
        for checkpoint in checkpoint_id:
            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,))
            checkpoints.append(db.fetchall())
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name, count = db.fetchall()[0]
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