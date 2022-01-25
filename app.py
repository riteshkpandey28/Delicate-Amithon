from flask import Flask, render_template, request, url_for, redirect, flash, g, session
import sqlite3
from flask_mail import Mail, Message
import random
from flask_socketio import SocketIO, join_room, leave_room
import time 
import text2emotion as te
from heapq import nlargest

app = Flask(__name__)
app.secret_key = 'ritesh'
socketio = SocketIO(app)

# --- CONFIGURATION FOR EMAIL NOTIFICATION --------
app.config['DEBUG'] = True
app.config['TESTION'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'delicate.alltoowell@gmail.com'
app.config['MAIL_PASSWORD'] = 'alltoowell'
app.config['MAIL_DEFAULT_SENDER'] = 'delicate.alltoowell@gmail.com'
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

mail = Mail(app)

database = './db.sqlite'

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start')
def start():
    return render_template('start.html')


# ------------------- COUNSELLOR LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.pop('user', None)

        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = '" +email+"' AND password = '"+password+"'")
        r = c.fetchone()

        print(r)

        if r != None:
            session['user'] = r[0]
            if r[4] == 'head':
                return redirect(url_for('head'))
            else:
                return redirect(url_for('counsellor'))
        else:
            flash("Invalid Email or Password", 'invalid')
        
        conn.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


# --------------- STUDENT REQUEST APPOINTMENT
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']

        conn = sqlite3.connect(database)
        c = conn.cursor()

        c.execute("SELECT username FROM appointments")
        rs = c.fetchall()
        for rs in rs:
            if username in rs:
                flash("Username already taken", 'validname')
                break
        else:
            c.execute("""INSERT INTO appointments (username, email) VALUES (?, ?)""", (username, email))
            conn.commit()
            flash("Your request has been sent to the counsellor. You will recieve further details on email", 'register')
        conn.close()

        return redirect(url_for('index'))
    return redirect(url_for('index'))


#  --------------- HEAD COUNSELLOR
@app.route('/head')
def head():
    if g.user:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = '"+str(session['user'])+"'")
        profile = c.fetchone()

        c.execute("SELECT * FROM appointments WHERE isbooked = '0'")
        requests = c.fetchall()

        c.execute("SELECT * FROM appointments WHERE date >= CURRENT_DATE AND isbooked = '1' AND counsellor = '"+str(session['user'])+"'")
        scheduled = c.fetchall()

        c.execute("SELECT COUNT(username) FROM appointments WHERE date < CURRENT_DATE AND counsellor = '"+str(session['user'])+"'")
        taken = c.fetchall()

        c.execute("SELECT COUNT(username) FROM appointments WHERE date >= CURRENT_DATE AND counsellor = '"+str(session['user'])+"'")
        scheduled_no = c.fetchall()
        

        context = {
            'profile': profile,
            'requests': requests,
            'scheduled': scheduled,
            'taken': taken,
            'scheduled_no': scheduled_no
        }
        return render_template('head_counsellor.html', **context)
    return redirect(url_for('index'))

@app.route('/head_book_appointment<int:id>', methods=['GET', 'POST'])
def head_book_appointment(id):
    if g.user:
        if request.method == 'POST':
            conn = sqlite3.connect(database)
            c = conn.cursor()

            c.execute("SELECT * FROM appointments WHERE id ='"+str(id)+"'")
            rs = c.fetchone()

            username = rs[1]
            email = rs[2]
            date = request.form['date']
            time = request.form['time']
            counsellor = request.form['counsellor']
            roomid = random.randint(100000, 999999)
            isbooked = 1

            c.execute("SELECT name FROM users WHERE id = '"+str(counsellor)+"'")
            counsellorname = c.fetchone()

            c.execute("""
            UPDATE appointments SET (isbooked, date, time, roomid, counsellor, counsellorname) = (?, ?, ?, ?, ?, ?) WHERE id = ?""", (isbooked, date, time, roomid, counsellor, counsellorname[0], id))

            conn.commit()
            conn.close()

            context = {
                'username': username,
                'date': date,
                'time': time,
                'roomid': roomid,
                'counsellorname': counsellorname[0]
            }

            msg = Message('DELICATE - Appointment Booked', recipients=[email])
            msg.html = render_template('email.html', **context)
            mail.send(msg)

        return redirect(url_for('head'))
    return redirect(url_for('index'))


#  --------------- COUNSELLOR
@app.route('/counsellor')
def counsellor():
    if g.user:
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = '"+str(session['user'])+"'")
        profile = c.fetchone()

        c.execute("SELECT * FROM appointments WHERE isbooked = '0'")
        requests = c.fetchall()

        c.execute("SELECT * FROM appointments WHERE date >= CURRENT_DATE AND isbooked = '1' AND counsellor = '"+str(session['user'])+"'")
        scheduled = c.fetchall()

        c.execute("SELECT COUNT(username) FROM appointments WHERE date < CURRENT_DATE AND counsellor = '"+str(session['user'])+"'")
        taken = c.fetchall()

        c.execute("SELECT COUNT(username) FROM appointments WHERE date >= CURRENT_DATE AND counsellor = '"+str(session['user'])+"'")
        scheduled_no = c.fetchall()
        
        context = {
            'profile': profile,
            'requests': requests,
            'scheduled': scheduled,
            'taken': taken,
            'scheduled_no': scheduled_no
        }
        return render_template('counsellor.html', **context)
    return redirect(url_for('index'))

@app.route('/book_appointment<int:id>', methods=['GET', 'POST'])
def book_appointment(id):
    if g.user:
        if request.method == 'POST':
            conn = sqlite3.connect(database)
            c = conn.cursor()

            c.execute("SELECT * FROM appointments WHERE id ='"+str(id)+"'")
            rs = c.fetchone()

            username = rs[1]
            email = rs[2]
            date = request.form['date']
            time = request.form['time']
            counsellor = session['user']
            roomid = random.randint(100000, 999999)
            isbooked = 1

            c.execute("SELECT name FROM users WHERE id = '"+str(counsellor)+"'")
            counsellorname = c.fetchone()

            c.execute("""
            UPDATE appointments SET (isbooked, date, time, roomid, counsellor, counsellorname) = (?, ?, ?, ?, ?, ?) WHERE id = ?""", (isbooked, date, time, roomid, counsellor, counsellorname[0], id))

            conn.commit()
            conn.close()

            context = {
                'username': username,
                'date': date,
                'time': time,
                'roomid': roomid,
                'counsellorname': counsellorname[0]
            }

            msg = Message('DELICATE - Appointment Booked', recipients=[email])
            msg.html = render_template('email.html', **context)
            mail.send(msg)

        return redirect(url_for('counsellor'))
    return redirect(url_for('index'))


# ----------------- RECOMMENDATION
@app.route('/recommendation', methods=['GET', 'POST'])
def recommendation():
    if request.method == 'POST':
        feelingText = request.form['feeling-text']
        feeling = te.get_emotion(feelingText)
        emotion = nlargest(1, feeling, key = feeling.get)
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM recomm WHERE emotion = +'"+emotion[0] +"'")
        recomm = c.fetchall()
        movie = random.randint(0, 4)
        book = random.randint(5, 9)
        music = random.randint(10, 14)
        context = {
            'emotion': emotion,
            'movie': recomm[movie],
            'music': recomm[music],
            'book': recomm[book],
        }
        return render_template('recommendation.html', **context)

    return render_template('recommendation.html')


# ------------------ CHAT
@app.route('/chat')
def chat():
    username = request.args.get('username')
    room = request.args.get('room')
    time_stamp = time.strftime('%b-%d %I:%M%p', time.localtime())
    return render_template('chat.html', username=username, room=room, time_stamp=time_stamp)

@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} has sent message to the room {}: {}".format(data['username'],
                                                                    data['room'],
                                                                    data['message']))
    socketio.emit('receive_message', data, room=data['room'])

@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    socketio.emit('join_room_announcement', data, room=data['room'])

@socketio.on('leave_room')
def handle_leave_room_event(data):
    app.logger.info("{} has left the room {}".format(data['username'], data['room']))
    leave_room(data['room'])
    socketio.emit('leave_room_announcement', data, room=data['room'])


@ app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session['user']

if __name__ == "__main__":
    app.run(debug=True)
    