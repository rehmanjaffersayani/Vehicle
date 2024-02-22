'''User class is used by flask-login and stores all information about the
currently logged in user'''
from flask import session
from flask_login import UserMixin
from flask_mysqldb import MySQL

mysql = MySQL()


class User(UserMixin):
    '''UserMixin contains all the flask-login defaults'''

    def __init__(self, user_id):
        self.id = user_id
        self.update()

    def update(self):
        '''Can be called whenever the user's information changes, so that the
        user object is up to date'''
        user_id = self.id

        cur = mysql.connect.cursor()

        cur.execute(
            '''SELECT u.first_name, u.last_name, u.email_address,
                u.default_location, u.wizard_id, l.name
            FROM users u
            LEFT JOIN locations l
                ON l.location_id = u.default_location
            WHERE user_id = %s''',
            (user_id,)
        )

        user = cur.fetchone()

        self.first_name = user['first_name']
        self.last_name = user['last_name']
        self.wizard_id = user['wizard_id']
        self.email_address = user['email_address']
        self.default_location = user['default_location']
        self.default_location_name = user['name']

    def get_location(self):
        '''Gets the users current location name'''
        def get_default():
            cur = mysql.connect.cursor()

            cur.execute(
                'SELECT name FROM locations WHERE location_id = %s',
                (self.default_location,)
            )

            result = cur.fetchone()

            if result is not None:
                location = result['name']
            else:
                location = 'All Locations'
            return location

        location = session.get('location', '')
        if location != 'All Locations':
            cur = mysql.connect.cursor()
            cur.execute(
                'SELECT name FROM locations WHERE name = %s',
                (location,)
            )
            result = cur.fetchone()
            if result is None or result['name'] is None or location == '':
                location = get_default()

        return location

    def set_location(self, location_id):
        '''Sets the users current location'''
        if location_id != '*':
            cur = mysql.connect.cursor()

            cur.execute(
                'SELECT name FROM locations WHERE location_id = %s',
                (location_id,)
            )

            result = cur.fetchone()

            session['location'] = result['name']
        else:
            session['location'] = 'All Locations'

    def get_group(self):
        '''Gets the users current group name'''
        group = session.get('group', '')

        cur = mysql.connect.cursor()
        cur.execute(
            'SELECT group_name FROM vehicle_groups WHERE group_name = %s',
            (group,)
        )
        result = cur.fetchone()
        if result is None or result['group_name'] is None or group == '':
            group = 'All Groups'

        return group

    def set_group(self, group_id):
        '''Sets the users current group'''

        if group_id != '*':
            cur = mysql.connect.cursor()

            cur.execute(
                'SELECT group_name FROM vehicle_groups WHERE group_id = %s',
                (group_id,)
            )

            result = cur.fetchone()

            session['group'] = result['group_name']
        else:
            session['group'] = 'All Groups'

    def has_role(self, role_name):
        '''Checks if a users has a given role'''
        cur = mysql.connect.cursor()

        cur.execute(
            '''SELECT ug.name
            FROM user_groups ug
            LEFT JOIN users_in_groups uig ON uig.group_id = ug.group_id
            WHERE uig.user_id = %s''',
            (self.id,)
        )

        roles = cur.fetchall()

        result = False
        for role in roles:
            if role['name'].lower() == role_name.lower():
                result = True
                break

        return result
