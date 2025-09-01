from flask import Flask, render_template, redirect, url_for, request, session, jsonify, abort, request, g
import sqlite3
from werkzeug.utils import secure_filename
from hashlib import sha256
import re
from math import trunc
import datetime
from dateutil.relativedelta import relativedelta
import os

# Globals

listy = ['hi', 'Any%', 'ARB', '100%', 'True Ending', 'Bny%', 'Cny%']
another_listy = [0.001, 1, 60, 3600]

with sqlite3.connect("times.db", check_same_thread=False) as database:
    db = database.cursor()
    app = Flask(__name__)
    app.secret_key = 'password'

    def time_clause(thing):  # Time words plural/singular e.g. 1 year, 2 years
        if thing == 1:
            return ''
        else:
            return 's'

    def sob_adder(user_id):  # Add SOB for each category
        sob_dict = {'Category': (('Time:', '#'), ('Time:', '#')),
                    'Any%': [], 'ARB': [], '100%': [], 'True Ending': [],
                    'Bny%': [], 'Cny%': []}
        
        for category in list(sob_dict.keys())[1:]:
            # For each category get the sum of a users checkpoint times in it
            db.execute('''SELECT SUM(time) AS sob FROM Run WHERE user_id = ?
                       AND type = "checkpoint"
                       AND category_id = (
                           SELECT id FROM Category WHERE name = ?);''',
                       (user_id, category))
            sob = db.fetchone()[0]
            
            db.execute('SELECT id FROM Category WHERE name = ?',
                       (category,))
            category_id = db.fetchone()[0]
            
            # Get the leaderboard of SOB checkpoint times for current category
            sob_leaderboard = ranker('ORDER by sum_of_bests ASC', category_id,
                                     'AND r1.type = "checkpoint"')
            
            print(sob_leaderboard)
            for time in sob_leaderboard:
                # If the current entry on leaderboard is same as user's entry
                if (time[2] == sob) and (user_id == time[0]):
                    sob_dict[category].append((
                        format_time_readable_form(
                            format_time_normal_form(sob)),
                        prefix_adder(sob_leaderboard.index(time)+1)))
                    # Add their time and rank to the dictionary
           
            if not sob_dict[category]:
                sob_dict[category].append((
                    format_time_readable_form(format_time_normal_form(sob)),
                    'N/A'))
                # Otherwise their time is invalid (Not completed)

            # For each category get the sum of a users IL times in it
            db.execute('''SELECT SUM(time) AS sob FROM Run WHERE user_id = ?
                       AND type = "IL"
                       AND category_id = ?''', (user_id, category_id))
            sob = db.fetchone()[0]
        
            # Get the leaderboard of SOB IL times for current category
            sob_leaderboard = ranker('ORDER by sum_of_bests ASC', category_id,
                                     'AND r1.type = "IL"')
           
            for time in sob_leaderboard:
                # If entry is the same as user time
                if (time[2] == sob) and (user_id == time[0]):
                    sob_dict[category].append((
                        format_time_readable_form(
                            format_time_normal_form(sob)),
                        prefix_adder(sob_leaderboard.index(time)+1)))
                    # Add their time and rank to leaderboard
  
            if len(sob_dict[category]) < 2:
                sob_dict[category].append((
                    format_time_readable_form(
                        format_time_normal_form(sob)),
                    'N/A'))
                # Otherwise their time is invalid (Not completed)
                
        print(sob_dict)
        return sob_dict
    
    def prefix_adder(num):  # Add bit at end of number for rank
        num = str(num)
        if num[-1] == '3':
            num = str(num) + 'rd'
            return num
        elif num[-1] == '2':
            num = str(num) + 'nd'
            return num
        elif num[-1] == '1':
            num = str(num) + 'st'
            return num
        else:
            num = str(num) + 'th'
            return num

    def format_time_normal_form(time):  # Turn time into mm:ss.msmsms
        if float(time) != 0:
            minutes = float(time)//60
            seconds = float(time) % 60
            
            milliseconds = float(time) - trunc(float(time))
            milliseconds = round(milliseconds, 3)
            milliseconds = str(milliseconds)[2:]
            time = f"{int(minutes)}:{int(seconds)}.{milliseconds}"
            
        else:
            time = 0

        return time
    
    def format_time_readable_form(time):  # Formatting the time
        # This function adds 0s to make more readable
        # E.g. mm:ss.msms into mm:ss.msmsmsms
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
    
    def format_time_second_form(time):  # Turn time into a ss.msmsms value
        total = 0
        total_individual_time = 0
        time_list = re.split('[.:]', str(time))
        backwards_time_list = reversed(time_list)
    
        for index, time_segment in enumerate(backwards_time_list):
            total_individual_time = 0
            # Digits store second values in a weird base in time values
            # E.g. If 56, 5 means 50 seconds.
            # Below calculates the amount of seconds each digit represents
            new_time = float(time_segment)*float(another_listy[index])
            total_individual_time += new_time
            total += total_individual_time
    
        total = int(total)
        total = str(total)
        total += '.'
        total += time_list[-1]
       
        return total
       
    def valid_time_checker(time):  # Checking if entered time is valid format
        has_colon = False
        for char in time:
            if str(char) not in '0123456789.:':
                print('invalid chars')
                return False
                
            if char == ':':
                has_colon = True
                
            if ':' in time:
                if char == '.' and not has_colon:
                    print('period before colon')
                    return False
                
        if time.count('.') > 1 or time.count('.') < 1:
            print('more or less than 1 period')
            return False
        
        if time.count(':') > 1:
            print('more than 1 colon')
            return False
        
        try:
            # This section will work if valid time but will break otherwise
            time_list = time.split('.')
            before_period = time_list[0]
            after_period = time_list[1]
            len_aft_p = len(str(after_period))
           
            if len_aft_p < 4 and len_aft_p > 0 and str(after_period).isdigit():
                pass
            
            else:
                print('more than 3 ms or none')
                return False
            
            print('did this')
            if ':' in time:
                time_segments = re.split('[.:]', time)
                print('splited')
                minutes = time_segments[0]
                
                if (len(str(minutes)) < 3 and
                   len(str(minutes)) > 0 and
                   str(minutes).isdigit() and int(minutes) < 60):
                    pass
               
                else:
                    print('more than 2 minutes or none')
                    return False
                
                seconds = time_segments[1]
                if (len(str(seconds)) < 3 and
                   len(str(seconds)) > 0 and
                   str(seconds).isdigit() and int(seconds) < 60):
                    pass
                
                else:
                    print('more than 2 seconds or none')
                    return False
            else:
                if (len(str(before_period)) < 3 and
                   len(str(before_period)) > 0 and
                   str(before_period).isdigit() and
                   int(before_period) < 60):
                    pass
                
                else:
                    print('seconds with no minutes more than 2 or none')
                    return False
                
            return True
        
        except:  # Bare except because can break in like literally every way
            return False
        
    def new_user_data(id):  # Populating database with entries for new user
        db.execute('SELECT id FROM Category;')
        results = db.fetchall()
        
        for category in results:
            category_id = category[0]
            chapter_listy = []
            db.execute('''SELECT checkpoint_id FROM CategoryCheckpoint
                       WHERE category_id = ?''',
                       (category_id,))
            checkpoints_list = db.fetchall()
            
            for checkpoint in checkpoints_list:
                db.execute('SELECT name FROM Checkpoint WHERE id = ?',
                           (checkpoint[0],))
                results = db.fetchone()
                name = results[0]
                
                chapter_name = (name.split(' '))[-1]
                if chapter_name not in chapter_listy:
                    chapter_listy.append(chapter_name)
                db.execute('SELECT id FROM Chapter WHERE name = ?',
                           (chapter_name,))
                results = db.fetchone()
                chapter_id = results[0]
                
                # For every checkpoint in game add an entry for new user
                db.execute('''INSERT INTO Run
                           (time, run_number, type,
                           chapter_id, user_id, category_id)
                           VALUES (0, ?, ?, ?, ?, ?)''',
                           (checkpoint[0], 'checkpoint',
                            chapter_id, id, category_id))
         
            for chapter in chapter_listy:
                db.execute('SELECT id FROM Chapter WHERE name = ?', (chapter,))
                chapter_id_real = db.fetchone()[0]
                
                # For every chapter in game add an entry for new user
                db.execute('''INSERT INTO Run
                           (time, run_number, type,
                           chapter_id, user_id, category_id)
                           VALUES (0, ?, ?, ?, ?, ?)''',
                           (-1, 'IL', chapter_id_real,
                            id, category_id))
            database.commit()

    def data_dictionary_creation(user_id, category_id, variable):
        # Make dictionary of a users times for specific category
        data_dictionary = {}
        # Get all the checkpoints in order of how they are run in the category
        db.execute('''SELECT checkpoint_id, orderer FROM CategoryCheckpoint
                   WHERE category_id = ? ORDER BY orderer ASC''',
                   (category_id,))
        results = db.fetchall()
        checkpoint_id = [j[0] for j in results]

        db.execute('''SELECT chapter_id FROM Run
                   WHERE type = "IL"
                   AND user_id = ? AND
                   category_id = ?;''',
                   (user_id, category_id))
        chapters_query = db.fetchall()
    
        data_dictionary['Chapter SOB'] = []
        placeholders = ', '.join('?' for i in chapters_query) 
        # Get names of chapters
        db.execute(f'''SELECT name FROM Chapter WHERE id IN (
            {placeholders})
            ORDER BY chapter_order ASC''',
            tuple(i[0] for i in chapters_query))
        new_chapters = db.fetchall()
       
        for index, chapter in enumerate(new_chapters):
            db.execute('SELECT id FROM Chapter WHERE name = ?', chapter)
            chapter_id = db.fetchone()[0]
            
            # Get all the IL times and add to the dictionary
            db.execute('''SELECT time FROM Run WHERE type = "IL"
                       AND user_id = ? AND
                       category_id = ? AND
                       chapter_id = ?''',
                       (user_id, category_id, chapter_id))
            IL_time = db.fetchone()[0]
            
            data_dictionary['Chapter SOB'].append([chapter[0]+' hi',
                                                   format_time_readable_form(
                                                       format_time_normal_form(
                                                           IL_time))])
        
        for checkpoint in checkpoint_id:
            # Get name of chapter that checkpoint is in
            db.execute('''SELECT name FROM Chapter WHERE id IN
                       (SELECT chapter_id FROM Run
                       WHERE run_number = ? AND
                       user_id = ? AND
                       category_id = ? AND
                       type = "checkpoint");''',
                       (checkpoint, user_id, category_id))
            results = db.fetchone()
           
            if results[0] not in data_dictionary:
                data_dictionary[results[0]] = []
            db.execute('SELECT name FROM checkpoint WHERE id = ?',
                       (checkpoint,))
            checkpoint_name = db.fetchone()
            #Get the time from that checkpoint
            db.execute('''SELECT time FROM Run WHERE user_id = ?
                       AND category_id = ? AND
                       run_number = ? AND
                       type = "checkpoint";''',
                       (user_id, category_id, checkpoint))
            time = db.fetchone()
            new_time = format_time_normal_form(time[0])
            # In the dictionary the keys are chapter names
            # Add the checkpoint time to its corresponding chapter that its in
            data_dictionary[results[0]].append([checkpoint_name[0],
                                                format_time_readable_form(
                                                    new_time)])
        if variable:  # For profile need a total time for each chapter
            for chapter in data_dictionary:
                final_time = 0
                for time_tuple in data_dictionary[chapter]:
                    if time_tuple[1] is not None:
                        final_time += round(float(
                            format_time_second_form(
                                time_tuple[1])), 3)
                        
                data_dictionary[chapter].append(('Total Total',
                                                 format_time_readable_form(
                                                     format_time_normal_form(
                                                         final_time))))

        print(data_dictionary)
        return data_dictionary
   
    def social_grabber(user_id):  # Get the socials from a user
        db.execute('''SELECT link, social_name FROM Socials WHERE
                   user_id = ?''', (user_id,))
        results = db.fetchall()
        return results

    def ranker(order_clause, category, type_clause):
        # Get the leaderboard of SOBs for everyone
        # Type clause is to determine whether IL SOB or checkpoint SOB
        # Order clause is something user can select - order by time or else
        db.execute(f'''
        SELECT r1.user_id, u.name, u.pfp_path, SUM(r1.time) AS sum_of_bests
        FROM Run r1
        JOIN User u ON r1.user_id = u.id
        WHERE r1.category_id = ?
        {type_clause}
        AND NOT EXISTS (
        SELECT 1
        FROM Run r2
        WHERE r2.user_id = r1.user_id
         
            AND r2.category_id = r1.category_id
            AND r2.type = r1.type
            AND (r2.time = 0 OR r2.time IS NULL)
        )
        GROUP BY r1.user_id
        {order_clause}''', (category,))
        rows = db.fetchall()
  
        return rows

    def comparison_data(user_id, category_id):
        data_dictionary_compare = data_dictionary_creation(
            user_id, category_id, False)
        
        db.execute('''SELECT SUM(time) AS sob FROM Run WHERE
                   user_id = ? AND
                   type = "IL" AND category_id = ?''',
                   (user_id, category_id))
        sob_compare = db.fetchone()[0]
        
        for j in data_dictionary_compare['Chapter SOB']:
            j[1] = float(format_time_second_form(j[1]))
        
        return (data_dictionary_compare, sob_compare)

    def check_session():
        user_session = session.get('user_id')
        if user_session:
            return True
        else:
            return False

    @app.errorhandler(404)
    def stoptryingtohack(i):
        return render_template('404.html')
   
    @app.before_request
    def check_login():
        user_id = session.get('user_id')
        g.user = None
        
        if user_id:
            db.execute('SELECT * FROM User WHERE id = ?', (user_id,))
            results = db.fetchall()
            
            g.user = results
        print(g.user, 'userglobal')
   
    @app.route('/get_comparison')
    def send_comparison_data():
        category_id = request.args.get('category')
        user_name = request.args.get('searched_name')
       
        db.execute('SELECT id FROM User WHERE name = ?;', (user_name,))
        user_id = db.fetchone()
        if user_id:
            real_user_id = user_id[0]
            data = comparison_data(real_user_id, category_id)
        else:
            data = comparison_data(26, category_id)
            user_name = 'benj'
   
        return jsonify([data, user_name])

    @app.route('/')
    def home():

        db.execute('''
                   SELECT COUNT(id)
                   FROM User
                   ''')
        counter = db.fetchall()
        db.execute('''
                    SELECT COUNT(*) AS total_completed_category_runs
                    FROM (
                    SELECT
                    r.user_id,
                    r.category_id
                    FROM Run r
                    WHERE r.type = "checkpoint"
                    GROUP BY r.user_id, r.category_id
                    
                    HAVING SUM(CASE WHEN r.time <= 0 OR r.time IS NULL THEN 1 ELSE 0 END) = 0
                    ) AS valid_categories;
                    ''')
        counter2 = db.fetchall()
       
        return render_template('home.html', title='Home',
                               counter=counter, counter2=counter2)
    
    @app.route('/about')
    def about():
        return render_template('about.html')
    
    @app.route('/get_leaderboard')
    def get_leaderboard():
        category = request.args.get('category', 'any%')
        sortby = request.args.get('sort', 'time')
        categoryName = request.args.get('categoryName', 1)
        
        db.execute('''
                   SELECT name FROM Category
                   WHERE id = ?
                   ''', (categoryName,))
        name = db.fetchone()
     
        order_clause = ''
        if sortby == 'alpha':
            order_clause = 'ORDER BY u.name ASC'
        
        else:
            order_clause = 'ORDER by sum_of_bests ASC'
            
        rows = ranker(order_clause, category, 'AND r1.type = "checkpoint"')
        #Query selects the sum of best for all user where they have filled in all their run entries for the category entered.
        #Grouped by users, and ordered by the smallest sum of best for the leaderboard.
     
        leaderboard = []
        leaderboard.append({'name': name[0]})
        print(rows)
        for index, row in enumerate(rows):
            if index == 0:
                best_time = row[3]
            time = format_time_readable_form(format_time_normal_form(row[3]))
            print(best_time, row[3])
            best = float(row[3])-float(best_time)
            best = format_time_readable_form(format_time_normal_form(best))
            best = f'+{best}'
            leaderboard.append({'username': row[1], 'sum_of_bests': time,
                                'profile': [row[0], category], 'pfp': row[2],
                                'best': best})
            #Add dictionaries to the leaderboard (this is the format js expects) containing the user name and their sum time.
        print(leaderboard)
        return jsonify(leaderboard)  # Return the created leaderboard to the js
        
    @app.route('/signup')
    def signup():
        return render_template('signup.html')
    
    @app.route('/signin')
    def signin():
        return render_template('signin.html')
    
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))
    
    @app.route('/new_user', methods=['POST'])
    def new_user():
        username = request.form.get('username')  # Get the items from the form
        password = request.form.get('password')
        if len(password) < 4 or len(password) > 20:
            abort(404)
        db.execute('SELECT id FROM user WHERE name = ?', (username,))
        if db.fetchall():
            abort(404)
        
        # Hashing the users password for security
        h = sha256()
        h.update(password.encode())
        hash = h.hexdigest()
        db.execute('SELECT id FROM user WHERE hash = ?', (hash,))
        if db.fetchall():
            abort(404)
        
        db.execute('''INSERT INTO User (
            name, hash, description, date_joined, pfp_path)
            VALUES (?, ?, ?, ?, ?)''',
            (username, hash, 'Tell us about Yourself!',
             datetime.datetime.now(), 'download.jpg'))
        
        database.commit()
        db.execute('SELECT id FROM User WHERE name == ?', (username,))
        results = db.fetchone()
        id = results[0]
      
        new_user_data(id)  # Running function to add all empty time entries for new user
        session.clear()
        return redirect(url_for('signin'))
    
    @app.route('/search', methods=['POST'])
    def search():
        searcher = None
        username = request.form.get('username')  # Get items from form
        password = request.form.get('password')
        search_username = request.form.get('search-username')
        
        print(username, search_username, password)
        if username and not search_username:
            searcher = username
        elif not username and search_username:
            searcher = search_username
            password = ''
        elif username and search_username:
            searcher = username
            print('hii')
            
        print(searcher)
        db.execute('SELECT id, hash FROM User WHERE name = ?;', (searcher,))
        results = db.fetchone()
        print('hiiiii', results)
        if results:  # If the user exists
            h = sha256()
            h.update(password.encode())
            hashed = h.hexdigest()
            user_id, hash = results
            if hash == hashed:
                session['user_id'] = user_id
            
                return redirect(url_for('get_times',
                                        user_id=user_id, category_id=1))
        
            return redirect(url_for('profile',
                                    user_id=user_id, category_id=1))
        
        print('No user found.')
        return redirect(url_for('home'))
    
    @app.route('/pfp/<int:user_id>/<int:category_id>', methods=['POST'])
    def new_pfp(user_id, category_id):
        file = request.files['pfp']
        
        pfp_directory = secure_filename(file.filename)
        file_path = os.path.join(
            'C:\dev\Celeste_Times_App_Repository\static\pfps', pfp_directory)
        file.save(file_path)
        
        db.execute('UPDATE User SET pfp_path = ? WHERE id = ?;',
                   (pfp_directory, user_id))
        database.commit()
        
        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))

    @app.route('/socials/<int:user_id>/<int:category_id>/<string:old_social_name>', methods=['POST'])
    def edit_socials(user_id, category_id, old_social_name):
        social_link = request.form.get('social_link')
        social_name = request.form.get('social_name')
        button_type = request.form.get('action')
        print(old_social_name)
        if button_type == 'edit':
            db.execute('''UPDATE Socials SET link = ?,
                       social_name = ?
                       WHERE user_id = ?
                       AND social_name = ?''',
                       (social_link, social_name, user_id, old_social_name))
        else:
            db.execute('''DELETE FROM Socials
                       WHERE user_id = ?
                       AND social_name = ?''',
                       (user_id, old_social_name))
            
        database.commit()
        
        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))
    
    @app.route('/add_socials/<int:user_id>/<int:category_id>', methods=['POST'])
    def add_socials(user_id, category_id):
        social_link = request.form.get('init_social')
        social_name = request.form.get('init_name')
        db.execute('SELECT COUNT(user_id) FROM Socials WHERE user_id = ?',
                   (user_id,))
        amount = db.fetchone()[0]
        
        if amount <= 3:
            db.execute('''INSERT INTO Socials (
                user_id, link, social_name)
                VALUES (?, ?, ?)''',
                (user_id, social_link, social_name))
            
            database.commit()
            
        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))
    
    @app.route('/descriptioner/<int:user_id>/<int:category_id>', methods=['POST'])
    def get_description(user_id, category_id):
        description = request.form.get('description')
        if len(description) <= 50:
            db.execute('UPDATE User SET description = ? WHERE id = ?',
                       (description, user_id))
            database.commit()
        else:
            print('>50')
            abort(404)
            
        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))

    @app.route('/get_times/<int:user_id>/<int:category_id>', methods=['GET', 'POST'])
    def get_times(user_id, category_id):
        if check_session():
            db.execute('SELECT date_joined FROM User WHERE id = ?',
                       (user_id,))
            current_time = datetime.datetime.now()
            member_since = relativedelta(current_time,
                                         datetime.datetime.strptime(
                                             db.fetchone()[0],
                                             "%Y-%m-%d %H:%M:%S.%f"))
            member_since = f"""{member_since.years}
            Year{time_clause(member_since.years)},
            {member_since.months}
            Month{time_clause(member_since.months)},
            and {member_since.days}
            Day{time_clause(member_since.days)} Ago"""
            
            results = social_grabber(user_id)
            data_dictionary = data_dictionary_creation(
                user_id, category_id, False)
            
            db.execute('SELECT name FROM category WHERE id = ?',
                       (category_id,))
            name = db.fetchall()[0]
            
            db.execute('SELECT name, description FROM user WHERE id = ?',
                       (user_id,))
            stuff = db.fetchall()
            user_name = stuff[0][0]
            user_description = stuff[0][1]
            
            sob_dict = sob_adder(user_id)
            
            return render_template('get_times.html',
                                   user_id=user_id,
                                   category_id=category_id,
                                   data_dictionary=data_dictionary,
                                   name=name, user_name=user_name,
                                   sob_dict=sob_dict,
                                   user_description=user_description,
                                   socials=results, member_since=member_since)
        else:
            abort(404)
   
    @app.route('/update_times/<int:user_id>/<int:category_id>', methods=['POST'])
    def update_times(user_id, category_id):
        if check_session():
            if request.method == 'POST':
                checkpoint_times = request.form.getlist('checkpoints[]')
                
                data_dictionary = data_dictionary_creation(
                    user_id, category_id, False)
            
                list_of_checkpoints = []
                print(data_dictionary)
                for chapter in data_dictionary:
                    for checkpoint_tuple in data_dictionary[chapter]:
                        if checkpoint_tuple[0] != 'Total Total':
                            list_of_checkpoints.append(checkpoint_tuple[0])
    
                for time, checkpoint in zip(checkpoint_times, list_of_checkpoints):
                    print('time', time, checkpoint)
                    if time != '':
                        if valid_time_checker(time):
                            time = format_time_second_form(time)
                            db.execute('''SELECT id FROM Checkpoint
                                       WHERE name = ?''',
                                       (checkpoint,))
                            results = db.fetchone()
                            
                            if results:
                                checkpoint_id = results[0]
                                db.execute('''UPDATE Run SET time = ?
                                           WHERE user_id = ?
                                           AND category_id = ?
                                           AND run_number = ?;''',
                                           (time, user_id,
                                            category_id, checkpoint_id))
                            else:
                                checkpoint = ' '.join(
                                    checkpoint.split(' ')[:-1])
                                
                                db.execute('''SELECT id FROM Chapter
                                           WHERE name = ?;''',
                                           (checkpoint,))
                                new_results = db.fetchone()[0]
                                
                                print(new_results)
                                db.execute('''UPDATE Run SET time = ?
                                           WHERE user_id = ?
                                           AND category_id = ?
                                           AND chapter_id = ?
                                           AND type = "IL";''',
                                           (time, user_id,
                                            category_id, new_results))
                            database.commit()
            
            return redirect(url_for('profile',
                                    user_id=user_id,
                                    category_id=category_id))
        else:
            abort(404)
   
    @app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET', 'POST'])
    def profile(user_id, category_id):
        db.execute('SELECT pfp_path FROM User WHERE id = ?',
                   (user_id,))
        pfp = db.fetchone()[0]
        
        print('pfp', pfp)
        if not pfp:
            pfp = 'download.png'
            
        db.execute('SELECT date_joined FROM User WHERE id = ?',
                   (user_id,))
        current_time = datetime.datetime.now()
        member_since = relativedelta(current_time,
                                     datetime.datetime.strptime(
                                         db.fetchone()[0],
                                         "%Y-%m-%d %H:%M:%S.%f"))
        
        member_since = f"""
        {member_since.years}
        Year{time_clause(member_since.years)},
        {member_since.months}
        Month{time_clause(member_since.months)},
        and {member_since.days}
        Day{time_clause(member_since.days)} Ago"""
        
        results = social_grabber(user_id)
        data_dictionary = data_dictionary_creation(user_id, category_id, True)
        db.execute('SELECT name FROM category WHERE id = ?', (category_id,))
        name = db.fetchall()[0]
        
        db.execute('SELECT name, description FROM user WHERE id = ?', (user_id,))
        stuff = db.fetchall()
        user_name = stuff[0][0]
        user_description = stuff[0][1]
        
        sob_dict = sob_adder(user_id)
        user_data_dictionary = data_dictionary_creation(user_id,
                                                        category_id, False)
        
        db.execute('''SELECT SUM(time) AS sob FROM Run
                   WHERE user_id = ?
                   AND type = "IL"
                   AND category_id = ?''',
                   (user_id, category_id))
        sob_compare_user = db.fetchone()[0]
        
        print(user_data_dictionary)
        for i in user_data_dictionary['Chapter SOB']:
            i[1] = float(format_time_second_form(i[1]))
            print(i[1])

        data_dictionary_compare, sob_compare = comparison_data(26, category_id)
           
        db.execute('''SELECT chapter_id FROM Run
                   WHERE type = "IL"
                   AND user_id = ?
                   AND category_id = ?;''',
                   (user_id, category_id))
        chapters_query = db.fetchall()
        print(chapters_query, 'chapters')
       
        placeholders = ', '.join('?' for i in chapters_query)
        db.execute(f'''SELECT name FROM Chapter
                   WHERE id IN ({placeholders})
                   ORDER BY chapter_order ASC''',
                   tuple(i[0] for i in chapters_query))
        new_chapters = db.fetchall()
        
        print('cha', new_chapters)
        chapters_list = []
        for i in new_chapters:
            chapters_list.append(i[0])

        print(user_data_dictionary)
        print(chapters_list)
        return render_template('profile.html', user_id=user_id,
                               category_id=category_id,
                               data_dictionary=data_dictionary,
                               name=name, user_name=user_name,
                               sob_dict=sob_dict,
                               user_description=user_description,
                               socials=results, member_since=member_since,
                               pfp=pfp,
                               user_data_dictionary=user_data_dictionary,
                               data_dictionary_compare=data_dictionary_compare,
                               sob_compare=float(sob_compare),
                               sob_compare_user=float(sob_compare_user),
                               chapters_list=chapters_list,
                               graph_x_labels=len(data_dictionary)-1,
                               compare_name='benj')

if __name__ == '__main__':
    app.run(debug=True)