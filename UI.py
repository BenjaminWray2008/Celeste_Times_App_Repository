from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
from werkzeug.security import check_password_hash

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
        user_name='thing requested from the form'
        user_password='other thing requested from the form'
        return render_template('home.html')
    
    @app.route('/search', methods=['POST'])
    def search():
        username = request.form.get('username')
        password = request.form.get('password')

        db.execute(f'SELECT id, hash FROM user WHERE name = {username};')
        results=db.fetchone()
        if results:

            user_id, hash = results
            print('hi')
            if check_password_hash(hash, password):
                return redirect(url_for('get_times',user_id=user_id, category_id=1))

            return render_template('profile.html', user_id = user_id, category_id = 1)
        
        print('No user found.')
        return render_template('home.html')

    @app.route('/get_times/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def input_times(user_id,category_id):
        checkpoints = []
        db.execute('SELECT time, run_number FROM Runs WHERE id = ? AND category_id = ?', (user_id, category_id))
        times = [row[0] for row in db.fetchall()]
        checkpoint_id = [row[1] for row in db.fetchall()]
        for checkpoint in checkpoint_id:
            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,))
            checkpoints.append(db.fetchall())
        return render_template('get_times.html', user_id=user_id, category_id=category_id, times=times, checkpoints=checkpoints)

    print('hi')
    @app.route('/update_times/<int:user_id>/<int:category_id>', methods=['POST'])
    def update_times(user_id,category_id):
         
        if 'submit_button' in request.form and request.method == 'POST':
            checkpoint_times=request.form.getlist('checkpoints[]')
        #get the times from the url
        #update the database
        return render_template('profile.html',user_id=user_id,category_id=category_id)
    
    @app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def profile(user_id, category_id):
        #If user selects a category change run this return statement:
        return redirect(url_for('profile', user_id=user_id, category_id=category_id))
        #If above condition is not true; render the template profile.html
        return render_template('profile.html',user_id=user_id,category_id=category_id)

if __name__ == '__main__':
    app.run(debug=True)