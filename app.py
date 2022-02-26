# -*- coding: utf-8 -*-
from flask import Flask, make_response, request, redirect, url_for, abort, session, jsonify
from jinja2.utils import generate_lorem_ipsum
from jinja2 import escape
from flask_sqlalchemy import SQLAlchemy
import os
import sys
import random
import pprint
import click
from flask import json
pp = pprint.PrettyPrinter(indent=4)
try:
    from urlparse import urlparse, urljoin
except ImportError:
    from urllib.parse import urlparse, urljoin


# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secret string')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', prefix + os.path.join(app.root_path, 'data.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

### MODELS ###


class TaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    desc = db.Column(db.Text)
    user_points = db.Column(db.Integer)
    carbon_savings = db.Column(db.Float)
    waste_savings = db.Column(db.Float)
    max_completions = db.Column(db.Integer)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    points = db.Column(db.Integer)
    tasks = db.relationship('Task')  # collection

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('task_template.id'))
    completed = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    num_completions = db.Column(db.Integer)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qn1 = db.Column(db.Text)
    qn2 = db.Column(db.Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class QuestionnaireAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    answer1 = db.Column(db.Text)
    answer2 = db.Column(db.Text)


def get_all_task_templates():
    tts = TaskTemplate.query.all()
    return tts


def get_task_history(userid=0):
    tasks = Task.query.filter(Task.user_id == userid).all()
    return tasks


def get_incomplete_tasks(userid=0):
    tasks = Task.query.filter(Task.user_id == userid,
                              Task.completed == False).all()
    return tasks


def get_completed_tasks(userid=0):
    tasks = Task.query.filter(Task.user_id == userid,
                              Task.completed == True).all()
    return tasks

###
# CLI COMMANDS
###


@app.cli.command("initdb")
@click.option('--drop', is_flag=True, help='Create after drop.')
def cli_initdb(drop):
    """Initialize the database."""
    if drop:
        db.drop_all()
    db.create_all()
    create_questions()
    create_task_templates()
    create_fakeusers()
    create_faketasks()
    click.echo('Initialized database.')


def create_questions():
    qns = [("Do you recycle at least 50% of recyclable products you use?", "How hard would it be for you to do that?"),
           ("Do you bring a bag to the supermarket?",
            "How hard would it be for you to do that?"),
           ("Do you eat meat?", "How hard would it be for you to do that?"),
           ("Do you fly more than twice a year?",
            "How hard would it be for you to do that?"),
           ("Do you avoid single-use food and drink containers and utensils?",
            "How hard would it be for you to do that?"),
           ("Do you drink milk?", "How hard would it be for you to do that?")]

    for d1, d2 in qns:
        q = Question(qn1=d1, qn2=d2)
        db.session.add(q)
    db.session.commit()


def create_task_templates():
    tasks = []
    tasks.append(TaskTemplate(
        desc="Recycle 4 items",
        user_points=10,
        carbon_savings=500.1,
        waste_savings=100.1,
        max_completions=4
    ))
    tasks.append(TaskTemplate(
        desc="Bring a bag to the supermarket twice",
        user_points=10,
        carbon_savings=500.1,
        waste_savings=100.1,
        max_completions=2
    ))
    tasks.append(TaskTemplate(
        desc="Don't eat meat for a day",
        user_points=10,
        carbon_savings=500.1,
        waste_savings=100.1,
        max_completions=1
    ))
    tasks.append(TaskTemplate(
        desc="Choose a flight that emits less carbon emissions",
        user_points=10,
        carbon_savings=500.1,
        waste_savings=100.1,
        max_completions=1
    ))
    tasks.append(TaskTemplate(
        desc="Decline using a single-use food or drink container or utensil once",
        user_points=10,
        carbon_savings=500.1,
        waste_savings=100.1,
        max_completions=1
    ))
    tasks.append(TaskTemplate(
        desc="Buy a carton of plant milk",
        user_points=10,
        carbon_savings=500.1,
        waste_savings=100.1,
        max_completions=1
    ))
    for t in tasks:
        db.session.add(t)
    db.session.commit()


def create_fakeusers():
    db.session.add(User(name="Bob", points=100))
    db.session.add(User(name="Alice", points=100))
    db.session.add(User(name="Jane", points=100))
    db.session.commit()


def create_faketasks():
    userid = User.query.filter(User.name == "Bob")[0].id
    print(f'Creating fake tasks for userid {userid}')
    t = Task(
        template_id=3,
        completed=True,
        user_id=userid,
        num_completions=1
    )
    db.session.add(t)
    t = Task(
        template_id=1,
        completed=True,
        user_id=userid,
        num_completions=4
    )
    db.session.add(t)
    t = Task(
        template_id=1,
        completed=False,
        user_id=userid,
        num_completions=2
    )
    db.session.add(t)
    t = Task(
        template_id=4,
        completed=False,
        user_id=userid,
        num_completions=0
    )
    db.session.add(t)
    db.session.commit()


def create_fakeanswers():
    # Create fake responses for 1:Bob
    userid = User.query.filter(User.name == "Bob")[0].id
    print(f'Creating fake questionnaire for userid {userid}')


@app.cli.command("adduser")
@click.argument("name")
def cli_newuser(name):
    u = User()
    u.name = name
    u.points = 100
    db.session.add(u)
    db.session.commit()
    click.echo('User added.')


@app.cli.command("getusers")
def cli_getusers():
    users = User.query.all()
    click.echo(f'Found {len(users)} users.')
    for u in users:
        click.echo(f'{u.id}: {u.name}')


@app.cli.command("gettasks")
@click.argument("userid")
def cli_gettasks(userid):
    tasks = get_task_history(userid)
    click.echo(f'Found {len(tasks)} tasks.')
    for t in tasks:
        click.echo(json.dumps(t.as_dict()))


@app.cli.command("getquestions")
def cli_getquestions():
    qns = Question.query.all()
    click.echo(f'Found {len(qns)} questions.')
    for q in qns:
        click.echo(f'{q.id}: {q.desc}')


@app.cli.command("gettasktemplates")
def cli_gettasktemplates():
    tts = TaskTemplate.query.all()
    click.echo(f'Found {len(tts)} task templates.')
    for t in tts:
        click.echo(f'{t.id}: {t.desc}')


######################


@app.route('/')
def root():
    response = "Nothing here, move along."
    return response


@app.route('/questionnaire', methods=['POST', 'GET'])
def questionnaire():
    if request.method == 'POST':
        request_data = request.get_json()

        for row in request_data["results"]:
            ans1, ans2 = "", ""
            if "answer1" in row:
                ans1 = row["answer1"]
            if "answer2" in row:
                ans2 = row["answer2"]
            ans = QuestionnaireAnswer(
                user_id=request_data["userId"],
                question_id=row["questionId"],
                answer1=ans1,
                answer2=ans2
            )
            db.session.add(ans)
        db.session.commit()
        pp.pprint(request_data)
        response = "POSTED"
    else:  # GET
        qns = Question.query.all()
        qns = [q.as_dict() for q in qns]
        response = app.response_class(
            response=json.dumps(qns),
            status=200,
            mimetype='application/json'
        )
    return response


# get name value from query string and cookie
@ app.route('/hello')
def hello():
    name = request.args.get('name')
    if name is None:
        name = request.cookies.get('name', 'Human')
    response = '<h1>Hello, %s!</h1>' % escape(name)  # escape name to avoid XSS
    # return different response according to the user's authentication status
    if 'logged_in' in session:
        response += '[Authenticated]'
    else:
        response += '[Not Authenticated]'
    return response


# redirect
@ app.route('/hi')
def hi():
    return redirect(url_for('hello'))


# use int URL converter
@ app.route('/goback/<int:year>')
def go_back(year):
    return 'Welcome to %d!' % (2018 - year)


# use any URL converter
@ app.route('/colors/<any(blue, white, red):color>')
def three_colors(color):
    return '<p>Love is patient and kind. Love is not jealous or boastful or proud or rude.</p>'


# return error response
@ app.route('/brew/<drink>')
def teapot(drink):
    if drink == 'coffee':
        abort(418)
    else:
        return 'A drop of tea.'


# 404
@ app.route('/404')
def not_found():
    abort(404)


# return response with different formats
@ app.route('/note', defaults={'content_type': 'text'})
@ app.route('/note/<content_type>')
def note(content_type):
    content_type = content_type.lower()
    if content_type == 'text':
        body = '''Note
to: Peter
from: Jane
heading: Reminder
body: Don't forget the party!
'''
        response = make_response(body)
        response.mimetype = 'text/plain'
    elif content_type == 'html':
        body = '''<!DOCTYPE html>
<html>
<head></head>
<body>
  <h1>Note</h1>
  <p>to: Peter</p>
  <p>from: Jane</p>
  <p>heading: Reminder</p>
  <p>body: <strong>Don't forget the party!</strong></p>
</body>
</html>
'''
        response = make_response(body)
        response.mimetype = 'text/html'
    elif content_type == 'xml':
        body = '''<?xml version="1.0" encoding="UTF-8"?>
<note>
  <to>Peter</to>
  <from>Jane</from>
  <heading>Reminder</heading>
  <body>Don't forget the party!</body>
</note>
'''
        response = make_response(body)
        response.mimetype = 'application/xml'
    elif content_type == 'json':
        body = {"note": {
            "to": "Peter",
            "from": "Jane",
            "heading": "Remider",
            "body": "Don't forget the party!"
        }
        }
        response = jsonify(body)
        # equal to:
        # response = make_response(json.dumps(body))
        # response.mimetype = "application/json"
    else:
        abort(400)
    return response


# set cookie
@ app.route('/set/<name>')
def set_cookie(name):
    response = make_response(redirect(url_for('hello')))
    response.set_cookie('name', name)
    return response


# log in user
@ app.route('/login')
def login():
    session['logged_in'] = True
    return redirect(url_for('hello'))


# protect view
@ app.route('/admin')
def admin():
    if 'logged_in' not in session:
        abort(403)
    return 'Welcome to admin page.'


# log out user
@ app.route('/logout')
def logout():
    if 'logged_in' in session:
        session.pop('logged_in')
    return redirect(url_for('hello'))


@ app.route('/more')
def load_post():
    return generate_lorem_ipsum(n=1)


# redirect to last page
@ app.route('/foo')
def foo():
    return '<h1>Foo page</h1><a href="%s">Do something and redirect</a>' \
           % url_for('do_something', next=request.full_path)


@ app.route('/bar')
def bar():
    return '<h1>Bar page</h1><a href="%s">Do something and redirect</a>' \
           % url_for('do_something', next=request.full_path)


@ app.route('/do-something')
def do_something():
    # do something here
    return redirect_back()


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def redirect_back(default='hello', **kwargs):
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return redirect(target)
    return redirect(url_for(default, **kwargs))
