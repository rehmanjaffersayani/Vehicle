import datetime

from flask_login import UserMixin

from . import db


class BookingChanges(db.Model):

    change_id = db.Column(db.Integer, primary_key=True)
    column_name = db.Column(db.String(20), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    editor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    edit_datetime = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    editor = db.relationship(
        'User', back_populates='changes', uselist=False, lazy=False)


class Bookings(db.Model):

    booking_id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(
        db.Integer, db.ForeignKey('locations.id'), nullable=False)
    resource_id = db.Column(db.Integer, nullable=False)
    resource_type = db.Column(db.String(7), nullable=False)
    wizard_id = db.Column(db.String(11), unique=True, nullable=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(12), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=False)
    creator_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    created = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    creator = db.relationship(
        'User', back_populates='bookings', uselist=False, lazy=False)
    location = db.relationship(
        'Locations', back_populates='bookings', uselist=False, lazy=False)

    def get_resource(self):
        if self.resource_type == 'vehicle':
            return Vehicles.query.get(self.resource_id)
        elif self.resource_type == 'group':
            return VehicleGroups.query.get(self.resource_id)


class Locations(db.Model):

    location_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    vehicles = db.relationship(
        'Vehicles', back_populates='location', lazy=True)
    bookings = db.relationship(
        'Bookings', back_populates='location', lazy=True)


class UserGroups(db.Model):

    group_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    in_groups = db.relationship(
        'UsersInGroups', back_populates='groups', lazy=True)


class User(db.Model, UserMixin):

    user_id = db.Column(db.Integer, primary_key=True)
    wizard_id = db.Column(db.String(12), unique=True, nullable=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email_address = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    default_location = db.Column(db.Integer, nullable=False, default=1)
    current_login_at = db.Column(db.DateTime, nullable=True)
    current_login_ip = db.Column(db.String(100), nullable=True)
    last_sign_in = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(200), nullable=True)
    login_count = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    changes = db.relationship(
        'BookingChanges', back_populates='editor', lazy=True)
    bookings = db.relationship('Bookings', back_populates='creator', lazy=True)
    in_groups = db.relationship(
        'UsersInGroups', back_populates='user', lazy=True)


class UsersInGroups(db.Model):

    join_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(
        db.Integer, db.ForeignKey('user_groups.id'), nullable=False)

    user = db.relationship(
        'User', back_populates='in_groups', uselist=False, lazy=False)
    group = db.relationship(
        'UserGroups', back_populates='in_groups', uselist=False, lazy=False)


class VehicleGroups(db.Model):

    group_id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(2), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    booking_color = db.bColumn(db.Integer, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    in_groups = db.relationship(
        'VehiclesInGroups', back_populates='group', lazy=True)


class Vehicles(db.Model):

    vehicle_id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(12), nullable=False)
    location_id = db.Column(
        db.Integer, db.ForeignKey('locations.id'), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    location = db.relationship(
        'Locations', back_populates='vehicles', uselist=False, lazy=False)
    in_groups = db.relationship(
        'VehiclesInGroups', back_populates='vehicle', lazy=True)


class VehiclesInGroups(db.Model):

    join_id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(
        db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    group_id = db.Column(
        db.Integer, db.ForeignKey('vehicle_groups.id'), nullable=False)

    vehicle = db.relationship(
        'Vehicles', back_populates='in_groups', uselist=False, lazy=False)
    group = db.relationship(
        'VehicleGroups', back_populates='in_groups', uselist=False, lazy=False)
