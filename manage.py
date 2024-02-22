'''Blueprint contains all endpoints for add/edit/remove for all
vehicles/groups/users/locations'''
from flask import Blueprint, Markup, jsonify, render_template, request
from flask_login import login_required
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash

from .auth import require_role

bp = Blueprint('manage', __name__, url_prefix='/manage')
mysql = MySQL()


@bp.route('/users')
@login_required
@require_role('manager')
def users():
    headers = [
        {'text': 'Manage'},
        {'text': 'Name'},
        {'text': 'Wizard ID'},
        {'text': 'Email'},
        {'text': 'Role'},
        {'text': 'Default Location'}
    ]

    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT u.user_id, u.wizard_id, u.first_name, u.last_name,
            u.email_address, l.name, u.active
        FROM users u
        LEFT JOIN locations l
            ON l.location_id = u.default_location'''
    )

    all_users = cur.fetchall()

    rows = []
    for user in all_users:

        if user['active'] == 1:
            cur.execute(
                '''SELECT g.name
                FROM users_in_groups ug
                LEFT JOIN user_groups g
                    ON g.group_id = ug.group_id
                WHERE ug.user_id = %s''',
                (user['user_id'],)
            )

            groups = []
            for group in cur.fetchall():
                groups.append(group['name'])

            manage = {'text': Markup(
                '<a href="#" edit>'
                + '<i class="fas fa-pencil-alt"></i> Edit</a>'
                + ' | '
                + '<a href="#" remove>'
                + '<i class="fas fa-trash-alt"></i> Remove</a>'
            )}
        else:
            groups = ['Inactive']
            manage = {
                'text': Markup('<a href="#" activate>'
                               + '<i class="fas fa-check"></i> Activate</a>')
            }

        rows.append({
            'data': [
                {
                    'name': 'id',
                    'value': user['user_id']
                },
                {
                    'name': 'first_name',
                    'value': user['first_name']
                },
                {
                    'name': 'last_name',
                    'value': user['last_name']
                },
            ],
            'cells': [
                manage,
                {'text': user['first_name'] + ' ' + user['last_name']},
                {'text': user['wizard_id']},
                {'text': user['email_address']},
                {'text': ', '.join(groups)},
                {'text': user['name']}
            ]
        })

    table = {
        'id': 'users',
        'headers': headers,
        'rows': rows
    }

    return render_template(
        'manage.html',
        title='Manage Users',
        table=table,
        form='user'
    )


@bp.route('/remove_user', methods=('POST',))
@login_required
@require_role('manager')
def remove_user():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE users SET active = 0 WHERE user_id = %s''',
        (request.form.get('user_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/activate_user', methods=('POST',))
@login_required
@require_role('manager')
def activate_user():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE users SET active = 1 WHERE user_id = %s''',
        (request.form.get('user_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/edit_user', methods=('POST',))
@login_required
@require_role('manager')
def edit_user():
    cur = mysql.connect.cursor()

    wizard_id = request.form.get('wizard_id')
    if wizard_id.strip() == '':
        wizard_id = None

    password = request.form.get('password', None)
    if password is not None and password != '':
        confirm = request.form.get('confirm_password')

        if password == confirm:
            new_password = request.form.get('new_password', None)
            confirm_password = request.form.get('confirm_password', None)
            if new_password == confirm_password:
                cur.execute(
                    '''UPDATE users
                    SET password_hash = %s
                    WHERE user_id = %s''',
                    (
                        generate_password_hash(new_password),
                        request.form.get('user_id')
                    )
                )

            cur.execute(
                '''UPDATE users SET
                    wizard_id = %s,
                    first_name = %s,
                    last_name = %s,
                    email_address = %s,
                    default_location = %s
                WHERE user_id = %s''',
                (
                    wizard_id,
                    request.form.get('first_name'),
                    request.form.get('last_name'),
                    request.form.get('email'),
                    request.form.get('location'),
                    request.form.get('user_id')
                )
            )

            cur.execute(
                '''UPDATE users_in_groups
                SET group_id = %s
                WHERE user_id = %s''',
                (
                    request.form.get('role'),
                    request.form.get('user_id')
                )
            )

            mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/vehicle_groups')
@login_required
@require_role('manager')
def vehicle_groups():
    headers = [
        {'text': 'Manage'},
        {'text': 'Group Name'},
        {'text': 'Budget Name'},
        {'text': 'Description'},
        {'text': 'Active'},
        {'text': 'Colour'}
    ]

    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT group_id, group_name, budget_name, description,
            HEX(booking_color) AS 'booking_color', active
        FROM vehicle_groups'''
    )

    all_groups = cur.fetchall()

    rows = []
    for group in all_groups:
        group['booking_color'] = group['booking_color'].rjust(6, '0')

        colors = Markup(
            '<span style="background-color: #'
            + group['booking_color']
            + '; width: 2em; display: block;">&nbsp;</span>'
        )

        if group['active'] == 1:
            active = 'Yes'
            manage = {'text': Markup(
                '<a href="#" edit>'
                + '<i class="fas fa-pencil-alt"></i> Edit</a>'
                + ' | '
                + '<a href="#" remove>'
                + '<i class="fas fa-trash-alt"></i> Remove</a>'
            )}
        else:
            active = 'No'
            manage = {
                'text': Markup('<a href="#" activate>'
                               + '<i class="fas fa-check"></i> Activate</a>')
            }

        rows.append({
            'data': [
                {
                    'name': 'id',
                    'value': group['group_id']
                },
                {
                    'name': 'booking_color',
                    'value': group['booking_color']
                }
            ],
            'cells': [
                manage,
                {'text': group['group_name']},
                {'text': group['budget_name']},
                {'text': group['description']},
                {'text': active},
                {'text': colors}
            ]
        })

    table = {
        'id': 'groups',
        'headers': headers,
        'rows': rows
    }

    return render_template(
        'manage.html',
        title='Manage Groups',
        table=table,
        form='group'
    )


@bp.route('/edit_group', methods=('POST',))
@login_required
@require_role('manager')
def edit_group():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE vehicle_groups SET
            group_name = %s,
            budget_name = %s,
            description = %s,
            booking_color = %s
        WHERE group_id = %s''',
        (
            request.form.get('name'),
            request.form.get('budget_name'),
            request.form.get('description'),
            int(request.form.get('booking_color').strip('#'), 16),
            request.form.get('group_id')
        )
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/add_group', methods=('POST',))
@login_required
@require_role('manager')
def add_group():
    cur = mysql.connect.cursor()

    cur.execute(
        '''INSERT INTO vehicle_groups (
            group_name, budget_name, description, booking_color
        ) VALUES (%s, %s, %s, %s)''',
        (
            request.form.get('name'),
            request.form.get('budget_name'),
            request.form.get('description'),
            int(request.form.get('booking_color').strip('#'), 16)
        )
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/remove_group', methods=('POST',))
@login_required
@require_role('manager')
def remove_group():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE vehicle_groups SET active = 0 WHERE group_id = %s''',
        (request.form.get('group_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/activate_group', methods=('POST',))
@login_required
@require_role('manager')
def activate_group():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE vehicle_groups SET active = 1 WHERE group_id = %s''',
        (request.form.get('group_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/locations')
@login_required
@require_role('manager')
def locations():
    headers = [
        {'text': 'Manage'},
        {'text': 'Name'},
        {'text': 'Active'}
    ]

    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT location_id, name, active
        FROM locations'''
    )

    all_locations = cur.fetchall()

    rows = []
    for location in all_locations:
        if location['active'] == 1:
            active = 'Yes'
            manage = {'text': Markup(
                '<a href="#" edit>'
                + '<i class="fas fa-pencil-alt"></i> Edit</a>'
                + ' | '
                + '<a href="#" remove>'
                + '<i class="fas fa-trash-alt"></i> Remove</a>'
            )}
        else:
            active = 'No'
            manage = {
                'text': Markup('<a href="#" activate>'
                               + '<i class="fas fa-check"></i> Activate</a>')
            }

        rows.append({
            'data': [
                {
                    'name': 'id',
                    'value': location['location_id']
                }
            ],
            'cells': [
                manage,
                {'text': location['name']},
                {'text': active}
            ]
        })

    table = {
        'id': 'locations',
        'headers': headers,
        'rows': rows
    }

    return render_template(
        'manage.html',
        title='Manage Locations',
        table=table,
        form='location'
    )


@bp.route('/edit_location', methods=('POST',))
@login_required
@require_role('manager')
def edit_location():
    cur = mysql.connect.cursor()

    cur.execute(
        'UPDATE locations SET name = %s WHERE location_id = %s',
        (
            request.form.get('name'),
            request.form.get('location_id')
        )
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/add_location', methods=('POST',))
@login_required
@require_role('manager')
def add_location():
    cur = mysql.connect.cursor()

    cur.execute(
        'INSERT INTO locations (name) VALUES (%s)',
        (request.form.get('name'),)
    )

    mysql.connect.commit()

    return jsonify({'success': True})


@bp.route('/remove_location', methods=('POST',))
@login_required
@require_role('manager')
def remove_location():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE locations SET active = 0 WHERE location_id = %s''',
        (request.form.get('location_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/activate_location', methods=('POST',))
@login_required
@require_role('manager')
def activate_location():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE locations SET active = 1 WHERE location_id = %s''',
        (request.form.get('location_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/vehicles')
@login_required
@require_role('manager')
def vehicles():
    headers = [
        {'text': 'Manage'},
        {'text': 'Registration'},
        {'text': 'Location'},
        {'text': 'Active'},
        {'text': 'Group'}
    ]

    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT v.vehicle_id, v.registration, v.active, l.name,
            vig.group_id, vg.group_name
        FROM vehicles v
        LEFT JOIN locations l
            ON l.location_id = v.location_id
        LEFT JOIN vehicles_in_groups vig
            ON vig.vehicle_id = v.vehicle_id
        LEFT JOIN vehicle_groups vg
            ON vig.group_id = vg.group_id'''
    )

    all_vehicles = cur.fetchall()

    rows = []
    for vehicle in all_vehicles:
        if vehicle['active'] == 1:
            active = 'Yes'
            manage = {'text': Markup(
                '<a href="#" edit>'
                + '<i class="fas fa-pencil-alt"></i> Edit</a>'
                + ' | '
                + '<a href="#" remove>'
                + '<i class="fas fa-trash-alt"></i> Remove</a>'
            )}
        else:
            active = 'No'
            manage = {
                'text': Markup('<a href="#" activate>'
                               + '<i class="fas fa-check"></i> Activate</a>')
            }

        rows.append({
            'data': [
                {
                    'name': 'id',
                    'value': vehicle['vehicle_id']
                },
                {
                    'name': 'group_id',
                    'value': vehicle['group_id']
                }
            ],
            'cells': [
                manage,
                {'text': vehicle['registration']},
                {'text': vehicle['name']},
                {'text': active},
                {'text': vehicle['group_name']}
            ]
        })

    table = {
        'id': 'vehicles',
        'headers': headers,
        'rows': rows
    }

    return render_template(
        'manage.html',
        title='Manage Vehicles',
        table=table,
        form='vehicle'
    )


@bp.route('/edit_vehicle', methods=('POST',))
@login_required
@require_role('manager')
def edit_vehicle():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE vehicles SET
            registration = %s,
            location_id = %s
        WHERE vehicle_id = %s''',
        (
            request.form.get('registration'),
            request.form.get('location'),
            request.form.get('vehicle_id')
        )
    )

    cur.execute(
        '''UPDATE vehicles_in_groups SET
            group_id = %s
        WHERE vehicle_id = %s''',
        (
            request.form.get('group'),
            request.form.get('vehicle_id')
        )
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/add_vehicle', methods=('POST',))
@login_required
@require_role('manager')
def add_vehicle():
    cur = mysql.connect.cursor()

    cur.execute(
        'INSERT INTO vehicles (registration, location_id) VALUES (%s, %s)',
        (
            request.form.get('registration'),
            request.form.get('location')
        )
    )

    cur.execute(
        '''INSERT INTO vehicles_in_groups (
            vehicle_id, group_id
        ) VALUES (%s, %s)''',
        (
            cur.lastrowid,
            request.form.get('group')
        )
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/remove_vehicle', methods=('POST',))
@login_required
@require_role('manager')
def remove_vehicle():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE vehicles SET active = 0 WHERE vehicle_id = %s''',
        (request.form.get('vehicle_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})


@bp.route('/activate_vehicle', methods=('POST',))
@login_required
@require_role('manager')
def activate_vehicle():
    cur = mysql.connect.cursor()

    cur.execute(
        '''UPDATE vehicles SET active = 1 WHERE vehicle_id = %s''',
        (request.form.get('vehicle_id'),)
    )

    mysql.connection.commit()

    return jsonify({'success': True})
