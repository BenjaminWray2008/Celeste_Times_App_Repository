from flask import Flask, render_template, redirect, url_for, request, session, jsonify, abort
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
    
    def sob_adder(user_id):
        sob_dict = {'Any%': '', 'ARB': '', '100%': '', 'True Ending': '', 'Bny%': '', 'Cny%': ''}
        for category in sob_dict:
            db.execute('SELECT SUM(time) AS sob FROM Run WHERE user_id = ? AND category_id = (SELECT id FROM Category WHERE name = ?);', (user_id, category))
            sob = db.fetchone()[0]
            sob_dict[category] = sob
     
        return sob_dict
    
    def format_time_normal_form(time):
       
        if float(time) != 0:
            minutes = float(time)//60
            seconds = float(time)%60
            
           
            milliseconds = float(time)-trunc(float(time))
         
            milliseconds = round(milliseconds, 3)
     
            milliseconds = str(milliseconds)[2:]
     
            time = f"{int(minutes)}:{int(seconds)}.{int(milliseconds)}"
        else:
            time = 0
        return time
    
    def format_time_readable_form(time):
        if time != 0:
            time = str(time)
            time_list = re.split('[.:]', time)
            minutes = time_list[0]
            seconds = time_list[1]
            ms = time_list[2]

            if len(str(minutes)) == 1:
                minutes = f'0{minutes}'
            
            if len(str(seconds)) == 1:
                seconds = f'0{seconds}'
            
            if len(str(ms)) < 3:
                length = len(str(ms))
                ms = f'{ms}{"0"*(3-length)}'
            time = f'{minutes}:{seconds}.{ms}'
            
        return time  
    
    def format_time_second_form(time):
    
        total=0
        total_individual_time=0
        time_list = re.split('[.:]', str(time))
 
        backwards_time_list = reversed(time_list)
    
        for index, time_segment in enumerate(backwards_time_list):
           
            total_individual_time = 0
    
            total_individual_time += (float(time_segment)*float(another_listy[index]))
 

            total += total_individual_time
    
        total = int(total)
        total = str(total)
   
        total += '.' 
        total += time_list[-1]
       
        return total    
       
    def valid_time_checker(time):
        has_colon = False
        for char in time:
            if str(char) not in '0123456789.:':
                print('invalid chars')
                return False
                
            if char == ':':
                has_colon = True
            if ':' in time:
                if char == '.' and has_colon == False:
                    print('period before colon')
                    return False
        if time.count('.') > 1 or time.count('.') < 1:
            print('more or less than 1 period')
            return False
        if time.count(':') > 1:
            print('more than 1 colon')
            return False
        

        try:
            time_list = time.split('.')
            before_period = time_list[0]; after_period = time_list[1]
            if (len(str(after_period)) < 4 and len(str(after_period)) > 0) and (str(after_period).isdigit()):
                pass
            else:
                print('more than 3 ms or none')
                return False
            print('did this')
            if ':' in time:
                time_segments = re.split('[.:]', time)
                print('splited')
                minutes = time_segments[0] 
                if (len(str(minutes)) < 3 and len(str(minutes)) > 0) and (str(minutes).isdigit()) and (int(minutes) < 60):
                    pass
                else:
                    print('more than 2 minutes or none')
                    return False
                seconds = time_segments[1]
                if (len(str(seconds)) < 3 and len(str(seconds)) > 0) and (str(seconds).isdigit() and (int(seconds) < 60)):
                    pass
                else:
                    print('more than 2 seconds or none')
                    return False
            else:
                if (len(str(before_period)) < 3 and len(str(before_period)) > 0) and (str(before_period).isdigit() and (int(before_period) < 60)):
                    pass
                else:
                    print('seconds with no minutes more than 2 or none')
                    return False
                
            return True
        except:
            return False
        
    def new_user_data(id):
        
        db.execute('SELECT id FROM Category;') #Getting all available categories
        results = db.fetchall()
        
        for category in results:
            category_id = category[0]
            db.execute('SELECT checkpoint_id FROM CategoryCheckpoint WHERE category_id = ?', (category_id,))
            checkpoints_list = db.fetchall() #For each category, getting a list of all checkpoints in that category
            
            for checkpoint in checkpoints_list:
                db.execute('SELECT name FROM Checkpoint WHERE id = ?', (checkpoint[0],)) #Formatting results
                results = db.fetchone()
                name = results[0]
                chapter_name = (name.split(' '))[-1]
                db.execute('SELECT id FROM Chapter WHERE name = ?', (chapter_name,))
                results = db.fetchone()
                chapter_id = results[0]
                
                db.execute('''INSERT INTO Run 
                           (time, run_number, type, chapter_id, user_id, category_id)
                           VALUES (0, ?, ?, ?, ?, ?)''',
                           (checkpoint[0], 'checkpoint', chapter_id, id, category_id)) #For every checkpoint for every category, inserting a run entry for the new user.
        database.commit()

    def data_dictionary_creation(user_id, category_id, variable):
        data_dictionary = {}
        db.execute('''SELECT checkpoint_id, orderer FROM CategoryCheckpoint 
                   WHERE category_id = ? ORDER BY orderer ASC''', (category_id,)) #Gets all checkpoints of a specific category in order of display
        results = db.fetchall()
        checkpoint_id = [j[0] for j in results]
        
        for checkpoint in checkpoint_id:
            db.execute('''SELECT name FROM Chapter WHERE id IN 
                       (SELECT chapter_id FROM Run 
                       WHERE run_number = ? AND user_id = ? AND category_id = ?);''', (checkpoint, user_id, category_id)) #For every checkpoint get the name of the chapter that it is in
            results = db.fetchone()
           
            if results[0] not in data_dictionary: #If the chapter is not already in the dictionary add it as an empty list
                data_dictionary[results[0]] = []
            db.execute('SELECT name FROM checkpoint WHERE id = ?', (checkpoint,)) #Get the name of the checkpoint and the time the user has for it
            checkpoint_name = db.fetchone()
            db.execute('SELECT time FROM Run WHERE user_id = ? AND category_id = ? AND run_number = ?;', (user_id, category_id, checkpoint))
            time = db.fetchone()
            print(time)
            new_time = format_time_normal_form(time[0]) #Turn time into mm:ss.msmsms form
            data_dictionary[results[0]].append((checkpoint_name[0], format_time_readable_form(new_time))) 
            #Add to the dictionary under the key of the chapter that is in, the checkpoint name and the time it corrresponds to
  
        if variable: 
            for chapter in data_dictionary:
                final_time = 0
                total = 0
                for time_tuple in data_dictionary[chapter]:
                    if time_tuple[1] is not None:
                        final_time += round(float(format_time_second_form(time_tuple[1])), 3)
                data_dictionary[chapter].append(('Total Total', format_time_readable_form(format_time_normal_form(final_time))))
        return data_dictionary
   
   
    @app.errorhandler(404)
    def stoptryingtohack(i):
        return render_template('404.html')
        
   
    @app.route('/')
    def home():
        
        return render_template('home.html', title='Home')
    
    @app.route('/get_leaderboard')
    def get_leaderboard():
        category = request.args.get('category', 'any%') #Get the category selected on the dropdown. Default is any%
 
        db.execute('''
        SELECT user_id, SUM(time) AS sum_of_bests
        FROM Run r1
        WHERE category_id = ?
        AND NOT EXISTS (
        SELECT 1
        FROM Run r2
        WHERE r2.user_id = r1.user_id
        AND r2.category_id = r1.category_id
        AND (r2.time = 0 OR r2.time IS NULL)
        )
        GROUP BY user_id
        ORDER BY sum_of_bests ASC''', (category,))
        #Query selects the sum of best for all user where they have filled in all their run entries for the category entered.
        #Grouped by users, and ordered by the smallest sum of best for the leaderboard.
     
        rows = db.fetchall()
        
        print(rows)
        leaderboard = []
        for row in rows:
            print(row[1])
            time = format_time_readable_form(format_time_normal_form(row[1]))
            db.execute('SELECT name FROM user WHERE id = ?', (row[0],))
            name = db.fetchone()[0]
            leaderboard.append({'username': name, 'sum_of_bests': time, 'profile':[row[0], category]}) 
            #Add dictionaries to the leaderboard (this is the format js expects) containing the user name and their sum time.
        
        return jsonify(leaderboard) #Return the created leaderboard to the js
     
        
    @app.route('/signup')
    def signup():
        return render_template('signup.html')
    
    @app.route('/new_user', methods=['POST'])
    def new_user():
        username = request.form.get('username') #Get the items from the form
        password = request.form.get('password')
        if len(password) < 4 or len(password) > 20:
            abort(404)
        db.execute('SELECT id FROM user WHERE name = ?', (username,))
        if db.fetchall():
            abort(404)
        
        #Hashing the users password for security
        h = sha256()
        h.update(password.encode())
        hash = h.hexdigest()
        db.execute('SELECT id FROM user WHERE hash = ?', (hash,))
        if db.fetchall():
            abort(404)
        db.execute('INSERT INTO User (name, hash) VALUES (?, ?)', (username, hash))
        database.commit()
        
        db.execute('SELECT id FROM User WHERE name == ?', (username,))
        results = db.fetchone()
        id = results[0]
      
        new_user_data(id) #Running function to add all empty time entries for new user
        return render_template('home.html')
    
    @app.route('/search', methods=['POST'])
    def search():
        username = request.form.get('username') #Get items from form
        password = request.form.get('password')

        db.execute(f'SELECT id, hash FROM User WHERE name = ?;', (username,)) #Get the actual hash of the username entered
        results=db.fetchone()
        
        if results: #If the user exists
            h = sha256()
            h.update(password.encode())
            hashed = h.hexdigest()
            user_id, hash = results #Work out the hash of the password entered
            if hash == hashed: #If the hashes are the same
           
            
                return redirect(url_for('get_times',user_id=user_id, category_id=1)) #Run page that lets user change times
        
            return redirect(url_for('profile',user_id=user_id,category_id=1)) #Else, run page that lets user view times
        
        print('No user found.') #If the username entered doesn't exist, reload home page.
        return render_template('home.html')

    @app.route('/get_times/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    
    def get_times(user_id,category_id):
        data_dictionary = data_dictionary_creation(user_id, category_id, False)
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
        db.execute('SELECT name FROM user WHERE id = ?', (user_id,))
        user_name = db.fetchall()[0]
     
        return render_template('get_times.html', user_id = user_id, category_id = category_id, data_dictionary = data_dictionary, name = name, user_name = user_name)

    @app.route('/update_times/<int:user_id>/<int:category_id>', methods=['POST'])
    def update_times(user_id,category_id):
        if request.method == 'POST':
            checkpoint_times=request.form.getlist('checkpoints[]') #Getting Form data
            data_dictionary = data_dictionary_creation(user_id, category_id, False) #Creating the dictionary of checkpoints
        
            list_of_checkpoints = []
            print(data_dictionary)
            for chapter in data_dictionary:
                
                for checkpoint_tuple in data_dictionary[chapter]:
                 
                    if checkpoint_tuple[0] != 'Total Total': #This tuple is created for total times for sections. This is not needed here
                        list_of_checkpoints.append(checkpoint_tuple[0])
  
            for time, checkpoint in zip(checkpoint_times, list_of_checkpoints): #Comparing the list of form data to the list of checkpoint names
                if time != '': #time is equal to '' if no time has been submitted
                   
                    if valid_time_checker(time): #If the time is valid
                        time = format_time_second_form(time) #Turns time into ss.msmsmsms
                        db.execute('SELECT id FROM Checkpoint WHERE name = ?', (checkpoint,))
                        results = db.fetchone()
                        checkpoint_id = results[0]
                        db.execute('UPDATE Run SET time = ? WHERE user_id = ? AND category_id = ? AND run_number = ?;',
                                   (time, user_id, category_id, checkpoint_id)) #Update the database with the new time
                        
                        database.commit()
        
        return redirect(url_for('profile',user_id=user_id,category_id=category_id))
    
    @app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET','POST'])
    def profile(user_id, category_id):
        data_dictionary = data_dictionary_creation(user_id, category_id, True)
        db.execute('SELECT name, count FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
        db.execute('SELECT name FROM user WHERE id = ?', (user_id,))
        user_name = db.fetchall()[0]
        sob_dict = sob_adder(user_id)
        return render_template('profile.html', user_id = user_id, category_id = category_id, data_dictionary = data_dictionary, name = name, user_name = user_name, sob_dict = sob_dict)

if __name__ == '__main__':
    app.run(debug=True)