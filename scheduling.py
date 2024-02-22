'''
Blue print contians all the endpoints used for scheduling and the
fullcalendar library
'''
import json
from datetime import datetime

from flask import Blueprint, Response, g, render_template, request
from flask_login import login_required
from flask_mysqldb import MySQL

bp = Blueprint('scheduling', __name__, url_prefix='/scheduling')
mysql = MySQL()


@bp.route('/index')
@login_required
def index():
    '''This page is basically just a javascript calendar'''

    # Start a mysql cursor
    cur = mysql.connect.cursor()

    # Get locations for when user creates a booking
    cur.execute(
        '''SELECT location_id, name
        FROM locations
        WHERE active = 1
        ORDER BY name ASC'''
    )
    locations = cur.fetchall()

    # User location
    user_location = g.user.get_location()

    # Render page
    return render_template(
        'fullcalendar.html',
        locations=locations,
        user_location=user_location
    )


@bp.route('/get_resources')
@login_required
def get_resources():
    resources = []
    cur = mysql.connect.cursor()

    group = g.user.get_group()
    if group == 'All Groups':
        cur.execute(
            '''SELECT group_id, group_name, budget_name, description,
                HEX(booking_color) AS 'booking_color'
            FROM vehicle_groups'''
        )
    else:
        cur.execute(
            '''SELECT group_id, group_name, budget_name, description,
                HEX(booking_color) AS 'booking_color'
            FROM vehicle_groups
            WHERE group_name = %s''',
            (group,)
        )
    groups = cur.fetchall()

    user_location = g.user.get_location()

    for group in groups:
        group['booking_color'] = '#' + group['booking_color'].rjust(6, '0')

        title = group['group_name'] + ' ' + group['budget_name']
        formatted_title = (
            '<span style="color:red;">' +
            group['group_name'] +
            '</span> <span style="color:blue;">' +
            group['budget_name'] +
            '</span>'
        )
        if title.strip() == '':
            title = group['description']
            formatted_title = title

        groupInfo = {
            'id': 'group_' + str(group['group_id']),
            'title': title,
            'formatted_title': formatted_title,
            'label': group['description'],
            'eventColor': group['booking_color']
        }

        if user_location != 'All Locations':
            cur.execute(
                '''SELECT v.vehicle_id, v.registration, l.name
                FROM vehicles v
                LEFT JOIN vehicles_in_groups g
                    ON g.vehicle_id = v.vehicle_id
                LEFT JOIN locations l
                    ON l.location_id = v.location_id
                WHERE g.group_id = %s AND l.name = %s''',
                (group['group_id'], user_location)
            )
        else:
            cur.execute(
                '''SELECT v.vehicle_id, v.registration, l.name
                FROM vehicles v
                LEFT JOIN vehicles_in_groups g
                    ON g.vehicle_id = v.vehicle_id
                LEFT JOIN locations l
                    ON l.location_id = v.location_id
                WHERE g.group_id = %s''',
                (group['group_id'],)
            )
        vehicles = cur.fetchall()

        children = []
        for vehicle in vehicles:
            children.append({
                'id': 'vehicle_' + str(vehicle['vehicle_id']),
                'title': vehicle['registration'],
                'label': vehicle['name'],
                'eventColor': group['booking_color']
            })

        if len(children) > 0:
            groupInfo['children'] = children

        resources.append(groupInfo)

    return Response(
        response=json.dumps(resources),
        status=200,
        mimetype="application/json"
    )


@bp.route('/get_events')
@login_required
def get_events():
    events = []
    cur = mysql.connect.cursor()
    user_location = g.user.get_location()
    print(user_location)

    if user_location != 'All Locations':
        cur.execute(
            '''SELECT location_id FROM locations WHERE name = %s''',
            (user_location,)
        )
        user_location = cur.fetchone()['location_id']

    cur.execute(
        '''SELECT booking_id, resource_id, resource_type, first_name,
            last_name, start_datetime, end_datetime, location_id
        FROM bookings
        WHERE start_datetime <= %s OR end_datetime >= %s''',
        (request.args.get('end'), request.args.get('start'))
    )
    bookings = cur.fetchall()

    for booking in bookings:
        if (
            user_location == 'All Locations'
            or booking['location_id'] is None
            or booking['location_id'] == user_location
        ):
            events.append({
                'id': booking['booking_id'],
                'resourceId': (
                    booking['resource_type'] + '_' +
                    str(booking['resource_id'])
                ),
                'start': (
                    booking['start_datetime'].strftime('%Y-%m-%dT%H:%M:%S')),
                'end': booking['end_datetime'].strftime('%Y-%m-%dT%H:%M:%S'),
                'title': booking['first_name'] + ' ' + booking['last_name']
            })

    return Response(
        response=json.dumps(events),
        status=200,
        mimetype="application/json"
    )


@bp.route('/get_locations')
@login_required
def get_locations():
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT location_id, name
        FROM locations
        WHERE active = 1
        ORDER BY name ASC'''
    )

    locations = cur.fetchall()

    options = [{
        'value': '*',
        'label': 'All Locations'
    }]
    current_location = g.user.get_location()
    for location in locations:
        loc_info = {
            'value': location['location_id'],
            'label': location['name']
        }

        if current_location == location['name']:
            loc_info['selected'] = True

        options.append(loc_info)

    return render_template(
        'select.html',
        id="locationChange",
        name="location",
        options=options
    )


@bp.route('/get_vehicle_groups')
@login_required
def get_vehicle_groups():
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT vg.group_id, vg.group_name, vg.description,
            COUNT(vig.vehicle_id) AS 'vehicles'
        FROM vehicle_groups vg
        LEFT JOIN vehicles_in_groups vig
            ON vig.group_id = vg.group_id
        GROUP BY vg.group_id, vig.group_id'''
    )

    groups = cur.fetchall()

    options = [{
        'value': '',
        'label': 'None',
        'selected': True,
        'disabled': True
    }]
    for group in groups:
        group_info = {
            'value': group['group_id'],
            'label': group['group_name'] + ' - ' + group['description'],
            'data': {
                'vehicles': 'No'
            }
        }

        if group['vehicles'] > 0:
            group_info['data']['vehicles'] = 'Yes'

        options.append(group_info)

    return render_template(
        'select.html',
        classes="form-control",
        required=True,
        name="vehicle_group",
        options=options
    )


@bp.route('/get_vehicles')
@login_required
def get_vehicles():
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT v.vehicle_id, v.registration
        FROM vehicles v
        LEFT JOIN vehicles_in_groups vig ON vig.vehicle_id = v.vehicle_id
        WHERE vig.group_id = %s''',
        (request.args.get('group'),)
    )

    vehicles = cur.fetchall()

    options = [{
        'value': '',
        'label': 'None',
        'selected': True
    }]
    for vehicle in vehicles:
        vehicle_info = {
            'value': vehicle['vehicle_id'],
            'label': vehicle['registration'],
        }

        options.append(vehicle_info)

    return render_template(
        'select.html',
        classes="form-control",
        name="vehicle",
        options=options
    )


@bp.route('/set_location', methods=('POST',))
@login_required
def set_location():
    g.user.set_location(request.form['location'])
    return json.dumps({'success': True})


@bp.route('/get_groups')
@login_required
def get_groups():
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT group_id, group_name, budget_name, description
        FROM vehicle_groups
        WHERE active = 1
        ORDER BY group_id ASC'''
    )

    groups = cur.fetchall()

    options = [{
        'value': '*',
        'label': 'All Groups'
    }]
    current_group = g.user.get_group()
    for group in groups:
        label = (
            group['group_name'] + ' ' + group['budget_name'] +
            ' | ' + group['description']
        )
        if label.split('|')[0].strip() == '':
            label = group['description']
        group_info = {
            'value': group['group_id'],
            'label': label
        }

        if current_group == group['group_name']:
            group_info['selected'] = True

        options.append(group_info)

    return render_template(
        'select.html',
        id="groupChange",
        name="group",
        options=options
    )


@bp.route('/set_group', methods=('POST',))
@login_required
def set_group():
    g.user.set_group(request.form['group'])
    return json.dumps({'success': True})


@bp.route('/create_booking', methods=('POST',))
@login_required
def create_booking():
    cur = mysql.connect.cursor()

    resource_id = request.form.get('vehicle_group')
    resource_type = request.form.get('resource_type')
    location_id = request.form.get('location_id')
    if request.form.get('vehicle') is None:
        resource_type = 'group'
    else:
        resource_id = request.form.get('vehicle')

    wizard_id = request.form.get('wizard_id')
    if wizard_id.strip() == "":
        wizard_id = None

    cur.execute(
        '''INSERT INTO bookings (
            resource_id, resource_type, wizard_id, first_name, last_name,
            phone_number, start_datetime, end_datetime, notes, creator_id,
            location_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        (
            resource_id,
            resource_type,
            wizard_id,
            request.form.get('first_name'),
            request.form.get('last_name'),
            request.form.get('phone_number'),
            request.form.get('start_datetime'),
            request.form.get('end_datetime'),
            request.form.get('notes'),
            g.user.id,
            location_id
        )
    )

    mysql.connect.commit()

    return json.dumps({'success': True})


@bp.route('/edit_booking', methods=('POST',))
@login_required
def edit_booking():
    cur = mysql.connect.cursor()

    booking_id = request.form.get('booking_id')

    cur.execute(
        '''SELECT resource_id, resource_type, wizard_id, first_name,
            last_name, phone_number, start_datetime, end_datetime, notes
        FROM bookings WHERE booking_id = %s''',
        (booking_id,)
    )

    current_booking = cur.fetchone()

    update = {
        'first_name': request.form.get('first_name'),
        'last_name': request.form.get('last_name'),
        'phone_number': request.form.get('phone_number'),
        'start_datetime': request.form.get('start_datetime'),
        'end_datetime': request.form.get('end_datetime'),
        'notes': request.form.get('notes')
    }

    update['resource_id'] = request.form.get('vehicle_group')
    update['resource_type'] = request.form.get('resource_type')
    if request.form.get('vehicle') is None:
        update['resource_type'] = 'group'
    else:
        update['resource_id'] = request.form.get('vehicle')

    update['wizard_id'] = request.form.get('wizard_id')
    if update['wizard_id'].strip() == "":
        update['wizard_id'] = None

    # Find differences
    columns = ['resource_id', 'resource_type', 'wizard_id', 'first_name',
               'last_name', 'phone_number', 'start_datetime', 'end_datetime',
               'notes']
    change_datetime = datetime.now()
    for column in columns:
        if str(update[column]) != str(current_booking[column]):
            cur.execute(
                '''INSERT INTO booking_changes (
                    column_name, old_value, new_value, editor_id, edit_datetime
                ) VALUES (%s, %s, %s, %s, %s)''',
                (
                    column,
                    current_booking[column],
                    update[column],
                    g.user.id,
                    change_datetime
                )
            )

    cur.execute(
        '''UPDATE bookings SET
            resource_id=%s,
            resource_type=%s,
            wizard_id=%s,
            first_name=%s,
            last_name=%s,
            phone_number=%s,
            start_datetime=%s,
            end_datetime=%s,
            notes=%s
        WHERE booking_id=%s''',
        (
            update['resource_id'],
            update['resource_type'],
            update['wizard_id'],
            update['first_name'],
            update['last_name'],
            update['phone_number'],
            update['start_datetime'],
            update['end_datetime'],
            update['notes'],
            booking_id
        )
    )

    mysql.connect.commit()

    return json.dumps({'success': True})


@bp.route('/move_booking', methods=('POST',))
@login_required
def move_booking():
    cur = mysql.connect.cursor()

    booking_id = request.form.get('booking_id')

    cur.execute(
        '''SELECT resource_id, resource_type
        FROM bookings WHERE booking_id = %s''',
        (booking_id,)
    )

    current_booking = cur.fetchone()

    update = {
        'resource_id': request.form.get('resource_id').split('_')[1],
        'resource_type': request.form.get('resource_id').split('_')[0]
    }

    # Find differences
    columns = ['resource_id', 'resource_type']
    change_datetime = datetime.now()
    for column in columns:
        if str(update[column]) != str(current_booking[column]):
            cur.execute(
                '''INSERT INTO booking_changes (
                    column_name, old_value, new_value, editor_id, edit_datetime
                ) VALUES (%s, %s, %s, %s, %s)''',
                (
                    column,
                    current_booking[column],
                    update[column],
                    g.user.id,
                    change_datetime
                )
            )

    cur.execute(
        '''UPDATE bookings SET
            resource_id=%s,
            resource_type=%s
        WHERE booking_id=%s''',
        (
            update['resource_id'],
            update['resource_type'],
            booking_id
        )
    )

    mysql.connect.commit()

    return json.dumps({'success': True})


@bp.route('/get_booking')
@login_required
def get_booking():
    cur = mysql.connect.cursor()

    cur.execute(
        '''SELECT b.booking_id, b.resource_id, b.resource_type,b. wizard_id,
            b.first_name, b.last_name, b.start_datetime, b.end_datetime,
            b.notes, b.created,  u.first_name AS creator_first,
            u.last_name AS creator_last
        FROM bookings b
        LEFT JOIN users u ON u.user_id = b.creator_id
        WHERE b.booking_id = %s''',
        (request.args.get('booking'),)
    )

    booking_info = cur.fetchone()

    group = ''

    if booking_info['resource_type'] == 'group':
        cur.execute(
            '''SELECT group_name, description
            FROM vehicle_groups
            WHERE group_id = %s''',
            (booking_info['resource_id'],)
        )

        group_info = cur.fetchone()

        group_id = booking_info['resource_id']
        vehicle_id = None

        group = (
            'Group ' + group_info['group_name']
            + ' - ' + group_info['description'])
    elif booking_info['resource_type'] == 'vehicle':
        cur.execute(
            '''SELECT vg.group_id, vg.group_name, v.registration
            FROM vehicles v
            LEFT JOIN vehicles_in_groups vig
                ON vig.vehicle_id = v.vehicle_id
            LEFT JOIN vehicle_groups vg
                ON vg.group_id = vig.group_id
            WHERE v.vehicle_id = %s''',
            (booking_info['resource_id'],)
        )

        vehicle_info = cur.fetchone()

        group_id = vehicle_info['group_id']
        vehicle_id = booking_info['resource_id']

        group = (
            'Group ' + vehicle_info['group_name']
            + ' - ' + vehicle_info['registration'])

    wizard_id = booking_info['wizard_id']
    if wizard_id is None or wizard_id == '':
        wizard_id = 'Not set'

    notes = booking_info['notes']
    if notes == '':
        notes = 'None'

    booking = {
        'id': booking_info['booking_id'],
        'first': booking_info['first_name'],
        'last': booking_info['last_name'],
        'wizard': wizard_id,
        'group': group,
        'group_id': group_id,
        'vehicle_id': vehicle_id,
        'start_date': str(booking_info['start_datetime']),
        'end_date': str(booking_info['end_datetime']),
        'notes': notes,
        'creator': (booking_info['creator_first'] + ' '
                    + booking_info['creator_last'])
    }

    return json.dumps(booking)
