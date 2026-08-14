from flask import Flask, render_template, redirect, url_for, request
import sqlite3
import random

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('pedair.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_all_cities():
    # Fetches a clean, sorted list of all unique origin cities in the database.
    conn = get_db_connection()
    cities_query = 'SELECT origin FROM flights UNION SELECT destination From flights ORDER BY origin ASC'
    
    # Extract the string value from each row row['origin']
    db_cities = [row['origin'] for row in  
    conn.execute(cities_query).fetchall()]
    conn.close()
    return db_cities


@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    if request.method == 'POST':
        origin = request.form.get('origin')
        dest = request.form.get('dest')
        db_flights = conn.execute('SELECT * FROM flights WHERE origin = ? AND destination = ?',(origin, dest)).fetchall()
    else:
        db_flights = conn.execute('SELECT * FROM flights').fetchall()
        origin,dest = "",""
    db_cities = get_all_cities()
    return render_template('index.html', flights=db_flights, cities = db_cities)
    

@app.route('/book/<int:flight_id>', methods=['GET', 'POST'])
def book_flight(flight_id):
    conn = get_db_connection()

    if request.method == 'POST':
        # 1. Capture the form text inputs using the HTML 'name' attributes
        first = request.form.get('first_name')
        last = request.form.get('last_name')
        email = request.form.get('email')
        passport = request.form.get('passport')

        # 2. Insert the customer into the passengers table securely using tuple syntax
        cursor = conn.cursor()
        #inserts new passenger if they don't already exist in the database
        cursor.execute('''
            INSERT INTO passengers (first_name, last_name, email, passport_num) 
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (
            SELECT 1 FROM passengers WHERE first_name = ? AND last_name = ? AND email = ? AND passport_num = ?
            );
        ''', (first, last, email, passport, first, last, email, passport))
        
        # Grab the passenger id that matches the details
        passenger_id = cursor.execute('SELECT passenger_id FROM passengers WHERE first_name = ? AND last_name = ? AND email = ? AND passport_num = ?', (first, last, email, passport)).fetchone()['passenger_id']

        # 3. Create a matching record in the bookings table to link passenger to flight
        seat = 'A1'
        capacity = cursor.execute("SELECT capacity FROM flights WHERE flight_id = ?",(flight_id,)).fetchone()[0] // 6
        #randomises seat until it is not taken
        while seat in {row[0] for row in cursor.execute("SELECT seat_assignment FROM bookings WHERE flight_id = ?",(flight_id,)).fetchall()}:
            seat = f'{random.randint(1,30)}{random.choice(["A", "B", "C", "D", "E", "F"])}'
        cursor.execute('''
            INSERT INTO bookings (flight_id, passenger_id, seat_assignment)
            VALUES (?, ?, ?)
        ''', (flight_id, passenger_id, seat))
        #grab booking id
        booking_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # 4. Redirect to confirmation after a successful database save
        return redirect(f"/confirmation/{booking_id}")

    else:
        # GET Request: Fetch the details of the specific flight to show on the form page
        flight = conn.execute('SELECT * FROM flights WHERE flight_id = ?', (flight_id,)).fetchone()
        conn.close()
        
        # Render the template and pass the specific flight object to it
        return render_template('booking.html', flight=flight)

@app.route('/confirmation/<int:booking_id>')
def booking_confirmation(booking_id):
    conn = get_db_connection()
    
    # SQL JOIN to grab Passenger, Flight, and Booking details in one query
    query = '''
        SELECT b.booking_id, b.seat_assignment, p.first_name, p.last_name, 
               f.origin, f.destination, f.departure_time, f.flight_id
        FROM bookings b
        JOIN passengers p ON b.passenger_id = p.passenger_id
        JOIN flights f ON b.flight_id = f.flight_id
        WHERE b.booking_id = ?
    '''
    booking_details = conn.execute(query, (booking_id,)).fetchone()
    conn.close()
    
    if booking_details is None:
        return "Booking Not Found", 404
        
    return render_template('booking_confirmation.html', booking=booking_details)

if __name__ == '__main__':
    app.run(debug=True)