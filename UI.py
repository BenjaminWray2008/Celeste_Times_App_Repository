from flask import (Flask, render_template, redirect,
                   url_for, request, session, jsonify, abort, g)
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


app = Flask(__name__)
app.secret_key = 'password'

def query(query, type, args=()):
    con = sqlite3.connect("times.db", check_same_thread=False)
    db = con.cursor()
    db.execute(query, args)
    if type == 'fetchall':
        result = db.fetchall()
        return result
    elif type == 'commit':
        con.commit()
        return
    else:
        result = db.fetchone()
        return result

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
        sob = query('''SELECT SUM(time) AS sob FROM Run WHERE user_id = ?
                    AND type = "checkpoint"
                    AND category_id = (
                        SELECT id FROM Category WHERE name = ?);''','fetchone',
                    (user_id, category))[0]

        category_id = query('SELECT id FROM Category WHERE name = ?', 'fetchone', 
                    (category,))[0]

        # Get the leaderboard of SOB checkpoint times for current category
        # This is helpful because can compare to find current users placing
        sob_leaderboard = ranker('ORDER by sum_of_bests ASC', category_id,
                                    'AND r1.type = "checkpoint"')
        print(category_id, sob_leaderboard, 'hiiiiiiii')
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
        sob = query('''SELECT SUM(time) AS sob FROM Run WHERE user_id = ?
                    AND type = "IL"
                    AND category_id = ?''', 'fetchone', (user_id, category_id))[0]

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
        hours = None

        if int(minutes) >= 60:  # If there are hours
            hours = int(minutes)//60  # Amount of hours
            minutes = int(minutes) - (hours*60)  # Resulting minutes

        if len(str(minutes)) == 1:
            minutes = f'0{minutes}'

        if len(str(seconds)) == 1:
            seconds = f'0{seconds}'

        if len(str(ms)) < 3:
            length = len(str(ms))
            ms = f'{ms}{"0"*(3-length)}'

        time = f'{minutes}:{seconds}.{ms}'

        if hours:
            time = f"{int(hours)}:{int(minutes)}:{int(seconds)}.{ms}"

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

    total = int(total)  # Get rid of decimal
    total = str(total)
    total += '.'  # Add milisecond value
    total += time_list[-1]

    return total

def valid_time_checker(time):  # Checking if entered time is valid format
    has_colon = False
    for char in time:
        if str(char) not in '0123456789.:':
            print('invalid chars')
            return False  # wrong cahracters

        if char == ':':
            has_colon = True

        if ':' in time:
            if char == '.' and not has_colon:
                print('period before colon')
                return False  # if there is a period before colon

    if time.count('.') > 1 or time.count('.') < 1:
        print('more or less than 1 period')
        return False

    if time.count(':') > 1:
        print('more than 1 colon')
        return False

    try:
        # This section will work if valid time but will break otherwise
        time_list = time.split('.')
        before_period = time_list[0]  # if valid is minutes+seconds
        after_period = time_list[1]  # if valid is milliseconds
        len_aft_p = len(str(after_period))

        if len_aft_p < 4 and len_aft_p > 0 and str(after_period).isdigit():
            pass

        else:
            print('more than 3 ms or none')
            return False  # invalid amount of milliseconds

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
                return False  # invalid amount of minutes

            seconds = time_segments[1]
            if (len(str(seconds)) < 3 and
                len(str(seconds)) > 0 and
                str(seconds).isdigit() and int(seconds) < 60):
                pass

            else:
                print('more than 2 seconds or none')
                return False  # invalid amount of seconds
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
    results = query('SELECT id FROM Category;', 'fetchall')

    for category in results:  # for all categories
        category_id = category[0]
        chapter_listy = []
        checkpoints_list = query('''SELECT checkpoint_id FROM CategoryCheckpoint
                    WHERE category_id = ?''', 'fetchall', 
                    (category_id,))
        # get all checkpoints from certain categories

        for checkpoint in checkpoints_list:
            results = query('SELECT name FROM Checkpoint WHERE id = ?', 'fetchone',
                        (checkpoint[0],))
            name = results[0]

            chapter_name = (name.split(' '))[-1]
            if chapter_name not in chapter_listy:
                chapter_listy.append(chapter_name)  # getting list of chapters
            results = query('SELECT id FROM Chapter WHERE name = ?', 'fetchone',
                        (chapter_name,))
            chapter_id = results[0]

            # For every checkpoint in game add an entry for new user
            query('''INSERT INTO Run
                        (time, run_number, type,
                        chapter_id, user_id, category_id)
                        VALUES (0, ?, ?, ?, ?, ?)''', 'commit',
                        (checkpoint[0], 'checkpoint',
                        chapter_id, id, category_id))

        for chapter in chapter_listy:
            chapter_id_real = query('SELECT id FROM Chapter WHERE name = ?', 'fetchone', (chapter,))[0]

            # For every chapter in game add an entry for new user
            query('''INSERT INTO Run
                        (time, run_number, type,
                        chapter_id, user_id, category_id)
                        VALUES (0, ?, ?, ?, ?, ?)''', 'commit',
                        (-1, 'IL', chapter_id_real,
                        id, category_id))

def data_dictionary_creation(user_id, category_id, variable):
    # Make dictionary of a users times for specific category
    data_dictionary = {}
    # Get all the checkpoints in order of how they are run in the category
    results = query('''SELECT checkpoint_id, orderer FROM CategoryCheckpoint
                WHERE category_id = ? ORDER BY orderer ASC''', 'fetchall',
                (category_id,))
    checkpoint_id = [j[0] for j in results]

    chapters_query = query('''SELECT chapter_id FROM Run
                WHERE type = "IL"
                AND user_id = ? AND
                category_id = ?;''', 'fetchall',
                (user_id, category_id))
    # all the chapter ids
    print(chapters_query, 'chaptersquery')

    data_dictionary['Chapter SOB'] = []
    placeholders = ', '.join('?' for i in chapters_query)
    print(placeholders, 'placeholders')
    # Get names of chapters in the category
    new_chapters = query(f'''SELECT name FROM Chapter WHERE id IN (
                {placeholders})
                ORDER BY chapter_order ASC''', 'fetchall',
                tuple(i[0] for i in chapters_query))
    print(new_chapters)
    for index, chapter in enumerate(new_chapters):
        chapter_id = query('SELECT id FROM Chapter WHERE name = ?', 'fetchone', (chapter[0],))[0]

        # Get all the IL times and add to the dictionary
        IL_time = query('''SELECT time FROM Run WHERE type = "IL"
                    AND user_id = ? AND
                    category_id = ? AND
                    chapter_id = ?''', 'fetchone',
                    (user_id, category_id, chapter_id))[0]

        data_dictionary['Chapter SOB'].append([chapter[0]+' hi',
                                                format_time_readable_form(
                                                    format_time_normal_form(
                                                        IL_time))])

    for checkpoint in checkpoint_id:
        # Get name of chapter that checkpoint is in
        results = query('''SELECT name FROM Chapter WHERE id IN
                    (SELECT chapter_id FROM Run
                    WHERE run_number = ? AND
                    user_id = ? AND
                    category_id = ? AND
                    type = "checkpoint");''', 'fetchone',
                    (checkpoint, user_id, category_id))

        if results[0] not in data_dictionary:
            data_dictionary[results[0]] = []  # add empty chapter list
        checkpoint_name = query('SELECT name FROM checkpoint WHERE id = ?', 'fetchone',
                    (checkpoint,))
        # Get the time from that checkpoint
        time = query('''SELECT time FROM Run WHERE user_id = ?
                    AND category_id = ? AND
                    run_number = ? AND
                    type = "checkpoint";''', 'fetchone',
                    (user_id, category_id, checkpoint))
        new_time = format_time_normal_form(time[0])
        # In the dictionary the keys are chapter names
        # Add the checkpoint time to its corresponding chapter that its in
        data_dictionary[results[0]].append([checkpoint_name[0],
                                            format_time_readable_form(
                                                new_time)])
    if variable:  # For if profile need a total time for each chapter
        for chapter in data_dictionary:
            final_time = 0
            for time_tuple in data_dictionary[chapter]:
                if time_tuple[1] is not None:
                    final_time += round(float(
                        format_time_second_form(
                            time_tuple[1])), 3)
            # For all checkpoints in each chapter add up if not None
            data_dictionary[chapter].append(('Total Total',
                                                format_time_readable_form(
                                                    format_time_normal_form(
                                                        final_time))))

    print(data_dictionary)
    return data_dictionary

def social_grabber(user_id):  # Get the socials from a user
    results = query('''SELECT link, social_name FROM Socials WHERE
                user_id = ?''', 'fetchall', (user_id,))
    return results

def ranker(order_clause, category, type_clause):
    # Get the leaderboard of SOBs for everyone
    # Type clause is to determine whether IL SOB or checkpoint SOB
    # Order clause is something user can select - order by time or else
    rows = query(f'''
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
    {order_clause}''', 'fetchall', (category,))
    # The AND NOT EXIST part of query made by ChatGPT

    return rows

def comparison_data(user_id, category_id):  # Info for different user
    data_dictionary_compare = data_dictionary_creation(
        user_id, category_id, False)

    # Get user's SOB
    sob_compare = query('''SELECT SUM(time) AS sob FROM Run WHERE
                user_id = ? AND
                type = "IL" AND category_id = ?''', 'fetchone',
                (user_id, category_id))[0]

    for j in data_dictionary_compare['Chapter SOB']:
        j[1] = float(format_time_second_form(j[1]))

    return (data_dictionary_compare, sob_compare)

def check_session():  # If user logged in
    user_session = session.get('user_id')
    if user_session:
        return True
    else:  # Will not let them access page
        return False

@app.errorhandler(404)
def stoptryingtohack(i):  # 404 page runner
    return render_template('404.html')

@app.errorhandler(405)
def methoderror(i):  # 405 page runner
    return render_template('405.html')

@app.before_request
def check_login():  # Gets global user data before running other pages
    user_id = session.get('user_id')  # current logged in user
    print('user', user_id)
    g.user = None

    if user_id:  # if a user is logged in
        results = query('SELECT * FROM User WHERE id = ?', 'fetchall', (user_id,))
        g.user = results  # logged in user data
    print(g.user, 'userglobal')

@app.route('/get_comparison')  # Generate data dictionary for searched user
def send_comparison_data():
    category_id = request.args.get('category')
    user_name = request.args.get('searched_name')

    results = query('SELECT name FROM category WHERE id = ?', 'fetchall', (category_id,))
    if results:
        pass
    else:
        category_id = 1

    user_id = query('SELECT id FROM User WHERE name = ?;', 'fetchone', (user_name,))
    if results:
        pass
    else:
        user_id = None

    if user_id:  # If search entered
        real_user_id = user_id[0]
        data = comparison_data(real_user_id, category_id)
    else:  # Default is person id 26
        data = comparison_data(26, category_id)
        user_name = 'benj'

    return jsonify([data, user_name])  # Return info to the js

@app.route('/')
def home():
    counter = query('''
                SELECT COUNT(id)
                FROM User
                ''', 'fetchall')
    # Total runners

    counter2 = query('''
                SELECT COUNT(*) AS total_completed_category_runs
                FROM (
                SELECT
                r.user_id,
                r.category_id
                FROM Run r
                WHERE r.type = "checkpoint"
                GROUP BY r.user_id, r.category_id

                HAVING SUM(
                    CASE WHEN r.time <= 0
                    OR r.time IS NULL THEN 1 ELSE 0 END) = 0
                ) AS valid_categories;
                ''', 'fetchall')
    # Total completed run entries
    # HAVING SUM section done by ChatGPT

    return render_template('home.html', title='Home',
                            counter=counter, counter2=counter2)

@app.route('/about')  # Page for about Celeste speedrunning
def about():
    return render_template('about.html')

@app.route('/get_leaderboard')  # Generate leaderboard for home page
def get_leaderboard():
    category = request.args.get('category', 1)
    sortby = request.args.get('sort', 'time')

    name = query('''
                SELECT name FROM Category
                WHERE id = ?
                ''', 'fetchone', (category,))
    # current category id
    if not name:
        name = ['Any%']
        category = 1

    order_clause = ''
    if sortby == 'alpha':
        order_clause = 'ORDER BY u.name ASC'

    else:
        order_clause = 'ORDER by sum_of_bests ASC'

    # Generate leaderboard
    rows = ranker(order_clause, category, 'AND r1.type = "checkpoint"')
    leaderboard = []
    leaderboard.append({'name': name[0]})
    print(rows)
    for index, row in enumerate(rows):  # Check how far from best entry
        if index == 0:
            best_time = row[3]
        # Current time
        time = format_time_readable_form(format_time_normal_form(row[3]))
        print(best_time, row[3])
        # Difference of current time from best time
        best = float(row[3])-float(best_time)
        best = format_time_readable_form(format_time_normal_form(best))
        best = f'+{best}'
        leaderboard.append({'username': row[1], 'sum_of_bests': time,
                            'profile': [row[0], category], 'pfp': row[2],
                            'best': best})
        # Add dictionaries to leaderboard - this is the format js expects
        # Each contains user name and their sum time.
    print(leaderboard)
    return jsonify(leaderboard)  # Return the created leaderboard to the js

@app.route('/signup')  # Page for signing up a user
def signup():
    if not session.get('user_id'):  # if not logged in
        return render_template('signup.html')
    else:
        return redirect(url_for('home'))

@app.route('/signin')  # Page for logging in a user
def signin():  # if not logged in
    if not session.get('user_id'):
        return render_template('signin.html')
    else:
        return redirect(url_for('home'))

@app.route('/logout')  # Route for logging out a user
def logout():
    session.clear()  # remove current user from session
    return redirect(url_for('home'))

@app.route('/new_user', methods=['POST'])  # Check if new user valid
def new_user():
    if request.method == 'POST':
        username = request.form.get('username')  # Get items from the form
        password = request.form.get('password')
        if len(password) < 4 or len(password) > 15:  # password conditions
            abort(404)
        if len(username) < 4 or len(username) > 15:  # username conditions
            abort(404)
        user_exist = query('SELECT id FROM user WHERE name = ?', 'fetchall', (username,))
        print(user_exist, 'userexzist')
        if user_exist:  # if username exists already
            return redirect(url_for('signup'))

        # Hashing the users password for security
        h = sha256()
        h.update(password.encode())
        hash = h.hexdigest()

        query('''INSERT INTO User (
                    name, hash, description, date_joined, pfp_path)
                    VALUES (?, ?, ?, ?, ?)''', 'commit',
                    (username, hash, 'Tell us about Yourself!',
                    datetime.datetime.now(), 'download.jpg'))
        # Entering new user into database

        results = query('SELECT id FROM User WHERE name == ?', 'fetchone', (username,))
        id = results[0]

        new_user_data(id)  # function to add empty time entries for user
        user_id = query('SELECT id from User WHERE name = ?;', 'fetchone', (username,))[0]
        session.clear()
        session['user_id'] = user_id  # log them in

        return redirect(url_for('get_times',  # Send to edit times page
                                user_id=user_id, category_id=1))
    else:
        abort(404)

@app.route('/search', methods=['POST'])  # Form for sending search data
def search():
    searcher = None
    username = request.form.get('username')  # Get items from form
    password = request.form.get('password')
    search_username = request.form.get('search-username')
    print(username, search_username, password)
    # Checking combinations to see who to search for / login as
    if username and not search_username:
        searcher = username
    elif not username and search_username:
        searcher = search_username
        password = ''
    elif username and search_username:
        searcher = username
        print('hii')

    print(searcher)
    results = query('SELECT id, hash FROM User WHERE name = ?;', 'fetchone', (searcher,))
    print('hiiiii', results)
    if results:  # If the user exists
        h = sha256()
        h.update(password.encode())
        hashed = h.hexdigest()
        user_id, hash = results
        if hash == hashed:  # If hashes match same password was entered
            session['user_id'] = user_id

            return redirect(url_for('get_times',  # Send to edit times page
                                    user_id=user_id, category_id=1))

        if not search_username and username:
            return redirect(url_for('signin'))  # invalid login reload signin
    
        return redirect(url_for('profile',  # Send to profile if searched user
                                user_id=user_id, category_id=1))

    print('No user found.')
    
    if search_username:
        return redirect(url_for('home'))  # No user found - reload homepage if was a search
    else:
        return redirect(url_for('signin'))  # invalid username reload signin

@app.route('/pfp/<int:user_id>/<int:category_id>', methods=['POST'])
def new_pfp(user_id, category_id):  # Add new pfp for user
    if check_session():
        file = request.files['pfp']  # Get the added file
        if not file.content_type.startswith('image/'):
            # if they tried to upload a file with inspect tool
            return redirect(url_for('get_times', user_id=user_id,
                            category_id=category_id))
        pfp_directory = secure_filename(file.filename)
        file_path = os.path.join(  # add the image to the pfps folder
            'C:\dev\Celeste_Times_App_Repository\static\pfps',
            pfp_directory)
        file.save(file_path)  # save it

        query('UPDATE User SET pfp_path = ? WHERE id = ?;', 'commit',
                    (pfp_directory, user_id))
        # Add new pfp path to database as users pfp

        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))
    else:
        abort(404)

@app.route('/socials/<int:user_id>/<int:category_id>/<path:old_social_name>', methods=['POST'])
def edit_socials(user_id, category_id, old_social_name):  # Edit socials
    if check_session():  # if not logged in
        social_link = request.form.get('social_link')
        social_name = request.form.get('social_name')
        button_type = request.form.get('action')
        print(old_social_name)
        if button_type == 'edit':  # If they changed an original link
            query('''UPDATE Socials SET link = ?,
                        social_name = ?
                        WHERE user_id = ?
                        AND social_name = ?''', 'commit',
                        (social_link, social_name, user_id, old_social_name))
        else:  # They must have deleted the link
            query('''DELETE FROM Socials
                        WHERE user_id = ?
                        AND social_name = ?''', 'commit',
                        (user_id, old_social_name))

        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))
    else:
        abort(404)

@app.route('/add_socials/<int:user_id>/<int:category_id>', methods=['POST'])
def add_socials(user_id, category_id):  # Created new social link
    if check_session():  # if not logged in
        social_link = request.form.get('init_social')
        social_name = request.form.get('init_name')
        amount = query('SELECT COUNT(user_id) FROM Socials WHERE user_id = ?', 'fetchone',
                    (user_id,))[0]
        # 4 socials max

        if amount <= 3 and social_link and social_name:
            query('''INSERT INTO Socials (
                        user_id, link, social_name)
                        VALUES (?, ?, ?)''', 'commit',
                        (user_id, social_link, social_name))
            # Add the new link

        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))
    else:
        abort(404)

@app.route('/descriptioner/<int:user_id>/<int:category_id>', methods=['POST'])
def get_description(user_id, category_id):  # Update a users description
    if check_session():  # if not logged in
        description = request.form.get('description')
        description = description.replace("\r\n", "")

        if len(description) <= 50:  # 50 is max description length
            query('UPDATE User SET description = ? WHERE id = ?', 'commit',
                        (description, user_id))
        else:
            print('>50')

        return redirect(url_for('get_times', user_id=user_id,
                                category_id=category_id))
    else:
        abort(404)

@app.route('/get_times/<int:user_id>/<int:category_id>', methods=['GET', 'POST'])
def get_times(user_id, category_id):  # Information for get_times page
    if check_session() and (user_id == g.user[0][0]):  # If logged in

        results = query('SELECT name from Category WHERE id = ?', 'fetchall',
                    (category_id,))
        if not results:
            category_id = 1

        date_joined_since = query('SELECT date_joined FROM User WHERE id = ?', 'fetchone',
                    (user_id,))[0]
        current_time = datetime.datetime.now()
        member_since = relativedelta(current_time,
                                        datetime.datetime.strptime(
                                            date_joined_since,
                                            "%Y-%m-%d %H:%M:%S.%f"))
        member_since = f"""{member_since.years}
        Year{time_clause(member_since.years)},
        {member_since.months}
        Month{time_clause(member_since.months)},
        and {member_since.days}
        Day{time_clause(member_since.days)} Ago"""
        # Above formatting results for how old is account

        results = social_grabber(user_id)  # Get users socials
        data_dictionary = data_dictionary_creation(
            user_id, category_id, False)  # Get users time data

        name = query('SELECT name FROM category WHERE id = ?', 'fetchall',
                    (category_id,))[0]
        # Current category name

        stuff = query('SELECT name, description FROM user WHERE id = ?', 'fetchall',
                    (user_id,))
        user_name = stuff[0][0]
        user_description = stuff[0][1]
        sob_dict = sob_adder(user_id)  # Get user SOBs
        print('socals', results)
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
def update_times(user_id, category_id):  # Update user times once submitted
    if check_session():  # If logged in
        if request.method == 'POST':
            # Get list of times and data dictionary to compare checkpoints
            checkpoint_times = request.form.getlist('checkpoints[]')
            data_dictionary = data_dictionary_creation(
                user_id, category_id, False)

            list_of_checkpoints = []
            print(data_dictionary)
            for chapter in data_dictionary:
                for checkpoint_tuple in data_dictionary[chapter]:
                    # For each checkpoint if its not a total add to list
                    if checkpoint_tuple[0] != 'Total Total':
                        list_of_checkpoints.append(checkpoint_tuple[0])

            # Compare each checkpoint with times gotten from submission
            for time, checkpoint in zip(checkpoint_times, list_of_checkpoints):
                print('time', time, checkpoint)
                if time != '':  # If the user submitted something
                    if valid_time_checker(time):  # If time correct format
                        time = format_time_second_form(time)
                        results = query('''SELECT id FROM Checkpoint
                                    WHERE name = ?''', 'fetchone',
                                    (checkpoint,))

                        if results:  # If its a checkpoint run
                            checkpoint_id = results[0]
                            # Update database with new time
                            query('''UPDATE Run SET time = ?
                                        WHERE user_id = ?
                                        AND category_id = ?
                                        AND run_number = ?;''', 'commit',
                                        (time, user_id,
                                        category_id, checkpoint_id))
                        else:  # Must be a chapter run
                            checkpoint = ' '.join(
                                checkpoint.split(' ')[:-1])

                            new_results = query('''SELECT id FROM Chapter
                                        WHERE name = ?;''', 'fetchone',
                                        (checkpoint,))[0]

                            print(new_results)
                            # Update database with new time
                            query('''UPDATE Run SET time = ?
                                        WHERE user_id = ?
                                        AND category_id = ?
                                        AND chapter_id = ?
                                        AND type = "IL";''', 'commit',
                                        (time, user_id,
                                        category_id, new_results))

        return redirect(url_for('profile',
                                user_id=user_id,
                                category_id=category_id))
    else:
        abort(404)

@app.route('/profile/<int:user_id>/<int:category_id>', methods=['GET', 'POST'])
def profile(user_id, category_id):  # User profile display
    results = query('SELECT name FROM user WHERE id = ?', 'fetchall', (user_id,))
    if not results:
        abort(404)

    results = query('SELECT name FROM Category WHERE id = ?', 'fetchall', (category_id,))
    if not results:
        abort(404)

    pfp = query('SELECT pfp_path FROM User WHERE id = ?', 'fetchone',
                (user_id,))[0]
    print('pfp', pfp)

    if not pfp:  # If user hasn't added a pfp
        pfp = 'download.png'  # use default

    # Get date since joined, socials, and time data
    date_joined_since = query('SELECT date_joined FROM User WHERE id = ?', 'fetchone',
                (user_id,))[0]
    current_time = datetime.datetime.now()
    # Find how long ago they signed up
    member_since = relativedelta(current_time,
                                    datetime.datetime.strptime(
                                        date_joined_since,
                                        "%Y-%m-%d %H:%M:%S.%f"))

    # Format that result
    member_since = f"""
    {member_since.years}
    Year{time_clause(member_since.years)},
    {member_since.months}
    Month{time_clause(member_since.months)},
    and {member_since.days}
    Day{time_clause(member_since.days)} Ago"""
    results = social_grabber(user_id)
    data_dictionary = data_dictionary_creation(user_id, category_id, True)

    name = query('SELECT name FROM category WHERE id = ?', 'fetchall', (category_id,))[0]
    # Current category name

    stuff = query('SELECT name, description FROM user WHERE id = ?', 'fetchall',
                (user_id,))
    user_name = stuff[0][0]
    user_description = stuff[0][1]

    sob_dict = sob_adder(user_id)  # user SOBs
    # User time data
    user_data_dictionary = data_dictionary_creation(user_id,
                                                    category_id, False)

    sob_compare_user = query('''SELECT SUM(time) AS sob FROM Run
                WHERE user_id = ?
                AND type = "IL"
                AND category_id = ?''', 'fetchone',
                (user_id, category_id))[0]
    # SOB for current category

    print(user_data_dictionary)
    for i in user_data_dictionary['Chapter SOB']:
        i[1] = float(format_time_second_form(i[1]))
        print(i[1])

    # Data for default comparison graph (id 26 is person with fastest time)
    data_dictionary_compare, sob_compare = comparison_data(26, category_id)

    # Section below get the x axis label chapters ordered correctly
    chapters_query = query('''SELECT chapter_id FROM Run
                WHERE type = "IL"
                AND user_id = ?
                AND category_id = ?;''', 'fetchall',
                (user_id, category_id))
    # get all chapters in category
    print(chapters_query, 'chapters')

    placeholders = ', '.join('?' for i in chapters_query)
    new_chapters = query(f'''SELECT name FROM Chapter
                WHERE id IN ({placeholders})
                ORDER BY chapter_order ASC''', 'fetchall',
                tuple(i[0] for i in chapters_query))
    # order those categories correctly
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
