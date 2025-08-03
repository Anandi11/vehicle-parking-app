from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
class User(db.Model):
    __tablename__ = 'users'
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True, nullable=False)
    email=db.Column(db.String(120), unique=True, nullable=False)
    password=db.Column(db.String(200), nullable=False)
    is_admin=db.Column(db.Boolean, default=False, nullable=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(100), nullable=False)
    address=db.Column(db.Text, nullable=False)
    pincode=db.Column(db.String(10), nullable=False)
    price_per_hour=db.Column(db.Float, nullable=False)
    max_spots=db.Column(db.Integer, nullable=False)
    spots=db.relationship('ParkingSpot', backref='parking_lot', lazy=True, cascade='all, delete-orphan')    
    @property
    def available_spots_count(self):
        return ParkingSpot.query.filter_by(lot_id=self.id, status='A').count()
    @property
    def occupied_spots_count(self):
        return ParkingSpot.query.filter_by(lot_id=self.id, status='O').count()

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    id=db.Column(db.Integer, primary_key=True)
    lot_id=db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_number=db.Column(db.String(10), nullable=False)
    status=db.Column(db.String(1), default='A', nullable=False)
    reservations=db.relationship('Reservation', backref='parking_spot', lazy=True, cascade='all, delete-orphan', passive_deletes=True)
    @property
    def current_reservation(self):
        return Reservation.query.filter_by(
            spot_id=self.id, 
            leaving_time=None
        ).first()

class Reservation(db.Model):
    __tablename__='reservations'
    id=db.Column(db.Integer, primary_key=True)
    spot_id=db.Column(db.Integer, db.ForeignKey('parking_spots.id', ondelete='CASCADE'), nullable=False)
    user_id=db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lot_id=db.Column(db.Integer, db.ForeignKey('parking_lots.id',ondelete='CASCADE'), nullable=False)
    vehicle_number=db.Column(db.String(20), nullable=False)
    parking_time=db.Column(db.DateTime, default=datetime.utcnow)
    leaving_time=db.Column(db.DateTime, nullable=True)
    total_cost=db.Column(db.Float, nullable=True)
    lot=db.relationship('ParkingLot', backref='reservations')
    @property
    def duration(self):
        if self.leaving_time:
            duration=self.leaving_time - self.parking_time
            return round(duration.total_seconds() / 3600, 2)
        else:
            duration=datetime.utcnow() - self.parking_time
            return round(duration.total_seconds() / 3600, 2)
    
    def calculate_cost(self, price_per_hour):
        if self.leaving_time:
            hours=self.duration
            if hours<1:
                hours=1
            return round(hours*price_per_hour, 2)
        return 0