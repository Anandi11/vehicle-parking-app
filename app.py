from flask import Flask, render_template, request, redirect, url_for, flash, session
from models.models import db, User, ParkingLot, ParkingSpot, Reservation
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_migrate import Migrate
from models.models import db

app=Flask(__name__)
app.config['SECRET_KEY']='eMtTf1105'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///parking_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db.init_app(app)
migrate=Migrate(app, db)
 
def create_admin():
    admin=User.query.filter_by(username='admin').first()
    if not admin:
        admin_user = User(
            username='admin',
            email='admin@parking.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.utcnow}
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username=request.form['username']
        password=request.form['password'] 
        user=User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id']=user.id
            session['username']=user.username
            session['is_admin']=user.is_admin
            if user.is_admin:
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            return render_template('login.html')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return render_template('register.html')
        
        new_user=User(
            username=username,
            email=email,
            password=generate_password_hash(password),
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/user/dashboard')
def user_dashboard():
    user=User.query.get(session['user_id'])
    parking_lots=ParkingLot.query.all()
    user_reservations=Reservation.query.filter_by(user_id=session['user_id']).order_by(Reservation.parking_time.desc()).limit(5).all()
    
    lot_summary = {}
    total_res = 0
    total_cost = 0.0
    for res in Reservation.query.filter_by(user_id=session['user_id']).all():
        lot_name = res.parking_spot.parking_lot.name
        lot_summary[lot_name]=lot_summary.get(lot_name, 0) + 1
        total_res+=1
        if res.total_cost:
            total_cost+=res.total_cost
    
    return render_template('user/user_dashboard.html', 
                         parking_lots=parking_lots,
                         reservations=user_reservations,
                         lot_summary=lot_summary,
                        total_reservations=total_res,
                        total_cost=round(total_cost, 2))

@app.route('/admin/dashboard')
def admin_dashboard():
    lots=ParkingLot.query.all()
    lot_summary = {
        lot.name: len(lot.reservations)
        for lot in lots
    }
    return render_template('admin/admin_dashboard.html', lots=lots, lot_summary=lot_summary)

@app.route('/admin/create_lot', methods=['GET', 'POST'])
def create_parking_lot():
    if request.method=='POST':
        name=request.form['name']
        price=float(request.form['price'])
        address=request.form['address']
        pincode=request.form['pincode']
        max_spots=int(request.form['spots'])

        new_lot=ParkingLot(
            name=name,
            address=address,
            pincode=pincode,
            price_per_hour=price,
            max_spots=max_spots
        )

        db.session.add(new_lot)
        db.session.commit()

        for i in range(1, max_spots + 1):
            spot=ParkingSpot(
                lot_id=new_lot.id,
                spot_number=f"Spot-{i}",
                status='A'
            )
            db.session.add(spot)
        db.session.commit()


        flash(f"Parking lot '{name}' created with {max_spots} spots!", 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/create_lot.html')

@app.route('/admin/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    lot=ParkingLot.query.get_or_404(lot_id)

    has_reservations=Reservation.query.join(ParkingSpot).filter(ParkingSpot.lot_id == lot.id).count()>0
    if has_reservations:
        flash("Cannot delete lot — reservations exist!", "danger")
        return redirect(url_for('admin_dashboard'))

    db.session.delete(lot)
    db.session.commit()
    flash(f"Parking lot '{lot.name}' deleted successfully!", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/modify_spots/<int:lot_id>', methods=['POST'])
def modify_spots(lot_id):
    lot=ParkingLot.query.get_or_404(lot_id)
    change_count=int(request.form.get('change_count', 1))
    action=request.form.get('action')
    if action=='increase':
        for i in range(change_count):
            spot = ParkingSpot(
                lot_id=lot.id,
                spot_number=f"S{lot.maximum_spots + i + 1}",
                status='A'
            )
            db.session.add(spot)
        lot.maximum_spots+=change_count
    elif action=='decrease':
        removable_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').order_by(ParkingSpot.id.desc()).limit(change_count).all()
        for spot in removable_spots:
            db.session.delete(spot)
        lot.maximum_spots-=len(removable_spots)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
def view_users():
    users=User.query.all()
    return render_template('admin/Users.html', users=users)

@app.route('/reserve/<int:lot_id>', methods=['GET','POST'])
def reserve_spot(lot_id):
    lot=ParkingLot.query.get_or_404(lot_id)

    if request.method=='POST':
        vehicle_number=request.form['vehicle_number']

        spot=ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

        if not spot:
            flash('No available spots in the selected lot.', 'danger')
            return redirect(url_for('user_dashboard'))

        spot.status='O'
        reservation=Reservation(
            user_id=session['user_id'],
            spot_id=spot.id,
            vehicle_number=vehicle_number,
            lot_id=lot.id
        )
        db.session.add(reservation)
        db.session.commit()

        flash(f'Spot {spot.spot_number} reserved successfully in {lot.name}.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('user/reserve_spot.html', lot=lot)

@app.route('/release/<int:reservation_id>', methods=['POST'])
def release_spot(reservation_id):
    reservation=Reservation.query.get_or_404(reservation_id)

    if reservation.leaving_time:
        flash("This reservation has already been released.", "warning")
        return redirect(url_for('user_dashboard'))

    reservation.leaving_time=datetime.utcnow()
    spot=ParkingSpot.query.get(reservation.spot_id)
    spot.status='A'

    lot=ParkingLot.query.get(spot.lot_id)
    reservation.total_cost=reservation.calculate_cost(lot.price_per_hour)
    reservation=Reservation.query.filter_by(spot_id=spot.id, user_id=session['user_id']).first()
    if reservation:
        db.session.delete(reservation)
    db.session.commit()

    flash(f"Spot released. Total cost: ₹{reservation.total_cost}", "info")
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

def init_db():
    with app.app_context():
        db.create_all()
        create_admin()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)