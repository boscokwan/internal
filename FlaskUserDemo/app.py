from re import sub
import uuid, os, hashlib
from flask import Flask, request, render_template, redirect, session, abort, flash
app = Flask(__name__)

# Register the setup page and import create_connection()
from utils import create_connection, setup
app.register_blueprint(setup)

@app.before_request
def restrict():
    restricted_pages = [
        'edit_users',
        'list_users',
        'view_user',
        'delete_user',
        'edit_subject',
        'list_subject',
        'view_subject'
    ]
    if 'logged_in' not in session and request.endpoint in restricted_pages:
        flash("You must be logged in to view this page.")
        return redirect('/login')

@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email=%s AND password=%s"
                values = (
                    request.form['email'],
                    encrypted_password
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
            session['logged_in'] = True
            session['first_name'] = result['first_name']
            session['role'] = result['role']
            session['id'] = result['user_id']
            return redirect("/dashboard")
        else:
            flash("Invalid username or password.")
            return redirect("/login")
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('login_html')

@app.route('/register', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
        else:
            avatar_filename = None

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO users
                    (first_name, last_name, email, password, avatar)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'], 
                    encrypted_password,
                    avatar_filename
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/')
    return render_template('users_add.html')

@app.route('/dashboard')
def list_users():
    if session['role'] != 'admin':
        flash("Only admin can access this page.")
        return redirect('/')
    with create_connection() as connection:
        with connection.cursor() as cursor:
            #cursor.execute("SELECT * FROM users JOIN subject_selection ON users.user_id = subject_selection.user_id")
            cursor.execute("SELECT * FROM subject_selection")
            selection_result = cursor.fetchall()
            cursor.execute("SELECT * FROM subject_info")
            info_result = cursor.fetchall()
            cursor.execute("SELECT * FROM users")
            users_result = cursor.fetchall()
            return render_template('users_list.html', users_result=users_result, selection_result=selection_result, info_result=info_result )

@app.route('/subject_information') # /subject_selections?user_id=123
def subject_information():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subject_info")
            result = cursor.fetchall()
    return render_template('subject_information.html', result=result)

@app.route('/subject_selection', methods=['GET', 'POST'])
def subject_selection():
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO subject_selection
                    (student_first_name, student_last_name, email,`must_choose_subject(english)`,`must_choose_subject(Mathematics)`, `must_choose_subject(science)`, `self_choose_subject(1)`,`self_choose_subject(2)` )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    request.form['must_choose_subject(english)'],
                    request.form['must_choose_subject(Mathematics)'],
                    request.form['must_choose_subject(science)'],
                    request.form['self_choose_subject(1)'],
                    request.form['self_choose_subject(2)']
                )
                cursor.execute(sql, values)
                connection.commit()
                return redirect('/')
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subject_info")
                subjects = cursor.fetchall()
        return render_template('subject_selection.html', subjects=subjects)

@app.route('/view')
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id=%s", request.args['user_id'])
            result = cursor.fetchone()
    return render_template('users_view.html', result=result)

@app.route('/delete')
def delete_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE user_id=%s", request.args['user_id'])
            connection.commit()
    return redirect('/dashboard')

@app.route('/edit', methods=['GET', 'POST'])
def edit_user():
    # Admin are allowed, users with the right id are allowed, everyone else sees 404.
    if session['role'] != 'admin' and str(session['user_id']) != request.args['user_id']:
        flash("You don't have permission to edit this user.")
        return redirect('/view?user_id=' + request.args['user_id'])

    if request.method == 'POST':
        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
            if request.form['old_avatar'] != 'None':
                os.remove("static/images/" + request.form['old_avatar'])
        elif request.form['old_avatar'] != 'None':
            avatar_filename = request.form['old_avatar']
        else:
            avatar_filename = None

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE users SET
                    first_name = %s,
                    last_name = %s,
                    email = %s
                WHERE id = %s"""
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/view?user_id=' + request.form['user_id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE user_id = %s", request.args['user_id'])
                result = cursor.fetchone()
        return render_template('users_edit.html', result=result)

    #usbject delete, add and edit
@app.route('/subject_view')
def view_subject():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subject_info WHERE subject_id=%s", request.args['subject_id'])
            result = cursor.fetchone()
    return render_template('subject_view.html', result=result)

@app.route('/subject_delete')
def delete_subject():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM subject_info WHERE subject_id=%s", request.args['subject_id'])
            connection.commit()
    return redirect('/dashboard')

@app.route('/subject_edit', methods=['GET', 'POST'])
def edit_subject():
    # Admin are allowed, users with the right id are allowed, everyone else sees 404.
    if session['role'] != 'admin' and str(session['subject_id']) != request.args['subject_id']:
        flash("You don't have permission to edit this user.")
        return redirect('/view?subject_id=' + request.args['subject_id'])

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE subject SET
                    subject_name = %s,
                    subeject_code = %s,
                    subject_categories = %s,
                    subject_descriptions = %s,
                    head_faculty_teachers = %s,
                WHERE subject_id = %s"""
                values = (
                    request.form['subject_name'],
                    request.form['subject_code'],
                    request.form['subject_categories'],
                    request.form['subject_description'],
                    request.form['head_faculty_teachers'],
                    request.form['subject_id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/view?subject_id=' + request.form['subject_id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subject_info WHERE subject_id = %s", request.args['subject_id'])
                result = cursor.fetchone()
        return render_template('subject_edit.html', result=result)

@app.route('/subject_register', methods=['GET', 'POST'])
def add_subject():
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO subject_info
                    (subject_name, subject_code, subject_categories, subject_description, head_faculty_teachers )
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form['subject_name'],
                    request.form['subject_code'],
                    request.form['subject_categories'], 
                    request.form['subject_description'],
                    request.form['head_faculty_teachers']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/')
    return render_template('subject_add.html')

@app.route('/subject_chaange', methods=['GET', 'POST '])
def change_subject():
    if request.method == 'POST':
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE subject SET
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    'must_choose_subject(Mathematics)' = %s,
                    'must_choose_subject(english)' = %s,
                    'must_choose_subject(science)' = %s,
                    'self_choose_subject(1)' = %s,
                    'self_choose_subject(2)' = %s,
                WHERE user_id = %s"""
                values = (
                    request.form['fisrt_name'],
                    request.form['last_name'],
                    request.form['email'],
                    request.form['must_choose_subject(english)'],
                    request.form['must_choose_subject(Mathematics)'],
                    request.form['must_choose_subject(science)'],
                    request.form['self_choose_subject(1)'],
                    request.form['self_choose_subject(2)']
                    )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/user_view?user_id=' + request.form['user_id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subject_selection WHERE user_id = %s", request.args['user_id'])
                result = cursor.fetchone()
        return render_template('subject_change.html', result=result)

if __name__ == '__main__':
    import os

    # This is required to allow sessions.
    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)