'''Blueprint contains all endpoints to do with user account/login'''
import functools
import json

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from flask_login import (fresh_login_required, login_required, login_user,
                         logout_user)
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

from .user import User

bp = Blueprint('auth', __name__)
mysql = MySQL()


def require_role(role_name):
    '''View wrapper so that we can require a certain role for that view'''
    def actual_decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if not g.user.has_role(role_name):
                abort(403)
            return view(**kwargs)
        return wrapped_view
    return actual_decorator


@bp.route('/add_user', methods=('POST',))
def add_user():
    '''Endpoint for registering a new user'''
    response = {}
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT email_address FROM users WHERE email_address = %s''',
        (request.form.get('email'),)
    )

    password = request.form.get('password')
    confirm = request.form.get('confirm_password')

    if not cur.rowcount and password == confirm:

        wizard_id = request.form.get('wizard_id')
        if wizard_id.strip() == '':
            wizard_id = None

        cur.execute(
            '''INSERT INTO users (
                wizard_id, first_name, last_name, email_address,
                password_hash, default_location
            ) VALUES (%s, %s, %s, %s, %s, %s)''',
            (
                wizard_id,
                request.form.get('first_name'),
                request.form.get('last_name'),
                request.form.get('email'),
                generate_password_hash(password),
                request.form.get('location')
            )
        )

        cur.execute(
            '''INSERT INTO users_in_groups (
                user_id, group_id
            ) VALUES (%s, %s)''',
            (
                cur.lastrowid,
                request.form.get('role')
            )
        )

        mysql.connect.commit()

        response = {'success': True}
    elif password != confirm:
        response = {
            'success': False,
            'message': 'Passwords do not match'
        }
    else:
        response = {
            'success': False,
            'message': 'Duplicate email address'
        }

    return json.dumps(response)


@bp.route('/login', methods=('GET', 'POST'))
def login():
    '''Login page'''
    print(mysql)
    print("-------- rehman")
    if request.method == 'POST':
        cur = mysql.connect.cursor()

        email = request.form['email']
        password = request.form['password']

        error = None
        cur.execute(
            '''SELECT user_id, password_hash
            FROM users
            WHERE active = 1 AND email_address = %s''',
            (email,)
        )
        user = cur.fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Incorrect password.'

        if error is None:
            cur.execute(
                '''UPDATE users SET
                    last_sign_in=current_login_at,
                    last_login_ip=current_login_ip,
                    login_count=login_count+1,
                    current_login_at=NOW(),
                    current_login_ip=%s
                WHERE user_id = %s''',
                (request.remote_addr, user['user_id'])
            )

            mysql.connect.commit()

            login_user(
                User(user['user_id']),
                remember=(request.form.get('remember') == 'yes')
            )

            return redirect(url_for('index'))

        flash(error)

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    '''Logout page, clears session and cookies'''
    # Clear session
    [session.pop(key) for key in list(session.keys()) if key != '_flashes']
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/user_preferences')
@fresh_login_required
def user_preferences():
    '''Page for viewing and editing user settings'''
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT location_id, name
        FROM locations
        WHERE active = 1
        ORDER BY name ASC'''
    )

    locations = cur.fetchall()

    select = []
    current_location = g.user.get_location()
    for location in locations:
        loc_info = {
            'value': location['location_id'],
            'label': location['name']
        }

        if current_location == location['name']:
            loc_info['selected'] = True

        select.append(loc_info)

    return render_template('preferences.html', select=select)


@bp.route('/update_preferences', methods=('POST',))
@fresh_login_required
def update_preferences():
    '''Actually updates user settings and redirects back to user_preferences'''
    cur = mysql.connect.cursor()

    email = g.user.email_address
    password = request.form.get('current_password')

    error = None
    cur.execute(
        '''SELECT user_id, password_hash
        FROM users
        WHERE active = 1 AND email_address = %s''',
        (email,)
    )
    user = cur.fetchone()

    if user is None:
        error = 'Incorrect username.'
    elif not check_password_hash(user['password_hash'], password):
        error = 'Incorrect password.'

    if error is None:
        cur.execute(
            '''UPDATE users SET
                wizard_id = %s,
                first_name = %s,
                last_name = %s,
                default_location = %s
            WHERE user_id = %s''',
            (
                request.form.get('wizard_id') or None,
                request.form.get('first_name'),
                request.form.get('last_name'),
                request.form.get('default_location'),
                g.user.id
            )
        )

        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if (
            new_password != ''
            and confirm_password != ''
            and new_password == confirm_password
        ):
            cur.execute(
                'UPDATE users SET password_hash = %s WHERE user_id = %s',
                (
                    generate_password_hash(new_password),
                    g.user.id
                )
            )

    mysql.connect.commit()
    g.user.update()

    return redirect(url_for('auth.user_preferences'))
