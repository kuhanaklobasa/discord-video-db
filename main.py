import math
import os
import random
import sqlite3

import flask
import requests
import werkzeug
from flask import request, session
from werkzeug.utils import secure_filename
from zenora import APIClient

import credentials

app = flask.Flask("Discord video database")
app.secret_key = "Shrek is the best person in the world"

client = APIClient(
    "DISCORD BOT TOKEN",
    client_secret=credentials.CLIENT_SECRET,
)

ALLOWED_EXTENSIONS = {'mp4', "webm", "mov", "avi"}

def gen_avatar(user_id):
    try:
        with requests.get(f"https://discord.com/api/v9/users/{user_id}", headers={"Authorization": "Bot DISCORD BOT TOKEN"}) as response:
            response = response.json()
            return f"https://cdn.discordapp.com/avatars/{user_id}/{response['avatar']}"
    except Exception as e:
        handle_bad_request("Bad request!")
        return None


@app.errorhandler(werkzeug.exceptions.BadRequest)
def handle_bad_request(msg):
    return msg, 400

@app.route("/")
def index():
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM videos")
        vids = cur.fetchall()
        print(vids)
        if not session.get("token"):
            return flask.render_template("index.html", vids=vids, math=math)
        else:
            with sqlite3.connect("database.db") as con:
                try:
                    bearer_client = APIClient(session["token"], bearer=True)
                    user = bearer_client.users.get_current_user()
                except Exception as e:
                    return handle_bad_request("Bad request!")
                cur = con.cursor()
                cur.execute("SELECT * FROM videos WHERE user_id = ?", (user.id,))
                vids = cur.fetchall()
                return flask.render_template("index.html", username=user.username, avatar=user.avatar_url, vids=vids, math=math)
@app.route("/profile")
def profile():
    if request.args.get("id") is None:
        if not session.get("token"):
            return flask.redirect("https://discord.com/api/oauth2/authorize?client_id=798151224058576906&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fcallback&response_type=code&scope=identify")
        with sqlite3.connect("database.db") as con:
            try:
                bearer_client = APIClient(session["token"], bearer=True)
                user = bearer_client.users.get_current_user()
            except Exception as e:
                return handle_bad_request("Bad request!")
            cur = con.cursor()
            cur.execute("SELECT * FROM videos WHERE user_id = ?", (user.id,))
            vids = cur.fetchall()
            return flask.render_template("profile.html", username=user.username, avatar=user.avatar_url, vids=vids, math=math, userdiscrim=user.username+"#"+user.discriminator, not_me=False)
    else:
        with sqlite3.connect("database.db") as con:
            try:
                with requests.get(f"https://discord.com/api/v9/users/{request.args.get('id')}", headers={"Authorization": "Bot BOT TOKEN"}) as response:
                    response = response.json()
                    print(response)
            except Exception as e:
                return handle_bad_request("Bad request!")
            cur = con.cursor()
            cur.execute("SELECT * FROM videos WHERE user_id = ?", (response["id"],))
            vids = cur.fetchall()
            return flask.render_template("profile.html", username=response["username"], avatar=f"https://cdn.discordapp.com/avatars/{request.args.get('id')}/{response['avatar']}" if response['avatar'] is not None else "https://archive.org/download/discordprofilepictures/discordgrey.png", vids=vids, math=math,userdiscrim=response['username']+"#"+response['discriminator'], not_me=True)

@app.route('/callback')
def callback():
    code = request.args.get("code")
    print(code)
    if not code:
        handle_bad_request("Bad request!")
    else:
        access_token = client.oauth.get_access_token(
            code, redirect_uri=credentials.REDIRECT_URI
        ).access_token
        session["token"] = access_token
        return flask.redirect("/")

@app.route('/upload')
def upload():
    if not session.get("token"):
        return flask.redirect("https://discord.com/api/oauth2/authorize?client_id=798151224058576906&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fcallback&response_type=code&scope=identify")
    else:
        try:
            bearer_client = APIClient(session["token"], bearer=True)
            user = bearer_client.users.get_current_user()
        except:
            handle_bad_request("Bad request!")
        return flask.render_template("upload.html", username=user.username, avatar=user.avatar_url)

def get_video(v_id):
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM videos WHERE file_id = ?", (int(v_id),))
        return cur.fetchone()

@app.route('/video')
def video():
    if request.args.get("id") is None:
        return flask.redirect("/")
    vid = get_video(request.args.get("id"))
    if not session.get("token"):
        avatar = gen_avatar(vid[3])
        return flask.render_template("video.html", title=vid[0], description=vid[1], avatar=avatar, author=vid[2], filename=vid[5], user_id=vid[3])
    else:
        try:
            bearer_client = APIClient(session["token"], bearer=True)
            user = bearer_client.users.get_current_user()
        except:
            handle_bad_request("Bad request!")
        return flask.render_template("video.html", username=user.username, avatar=user.avatar_url, title=vid[0], description=vid[1], author=vid[2], filename=vid[5], user_id=vid[3])

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/signout")
def signout():
    session.clear()
    return flask.redirect("/")

@app.post('/upload_file')
def upload_file():
    if not session.get("token"):
        return flask.redirect("https://discord.com/api/oauth2/authorize?client_id=798151224058576906&redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fcallback&response_type=code&scope=identify")
    else:
        if list(request.form.keys()) == ["title", "description"] and request.files.get("file") is not None:
            for entry in request.form:
                if entry is None:
                    return handle_bad_request("Bad request!")
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join("./static/uploads", filename))
                with sqlite3.connect("database.db") as con:
                    cur = con.cursor()

                    cur.execute("SELECT file_id FROM videos")
                    ids = cur.fetchall()
                    id = random.randint(100000000,999999999)
                    if id in ids:
                        id = random.randint(100000000,999999999)
                    try:
                        bearer_client = APIClient(session["token"], bearer=True)
                        user = bearer_client.users.get_current_user()
                    except Exception as e:
                        return handle_bad_request("Bad request!")
                    cur.execute("INSERT INTO videos(title, description, author, user_id, file_id, file_name) VALUES(?,?,?,?,?,?)", (request.form["title"], request.form["description"],user.username+"#"+user.discriminator , user.id, id, filename))
                    con.commit()
                    cur.close()
                    return flask.render_template("uploaded.html", id=str(id), msg=None)
            else:
                return flask.render_template("uploaded.html", msg="Incorrect file type")
        else:
            return handle_bad_request("Bad request!")





app.run("127.0.0.1",8000, debug=True)