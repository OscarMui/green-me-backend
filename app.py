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
from task_recommender import *


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

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    points = db.Column(db.Integer)
    tasks = db.relationship('Task')  # collection
    sub = db.Column(db.Text)  # from oauth

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
    subquestion_option = db.Column(db.Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    answer1 = db.Column(db.Text)
    answer2 = db.Column(db.Text)

############################
### Functions for Viktor ###
############################


def get_all_task_templates():
    tts = TaskTemplate.query.all()
    return tts


def get_template(templateid=0):
    template = TaskTemplate.query.get(templateid)
    return template


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


def get_task(taskid=0):
    tasks = Task.query.filter(Task.id == taskid).all()
    if len(tasks) == 0:
        return None
    return tasks[0]


def get_questionnaire_responses(userid=0):
    responses = QuestionnaireResponse.query.filter(
        QuestionnaireResponse.user_id == userid).all()
    return responses


def get_all_questions():
    qns = Question.query.all()
    d = {}
    for q in qns:
        d[q.id] = q
    return d


################
# CLI COMMANDS #
################


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
    create_fakeanswers()
    click.echo('Initialized database.')


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
        click.echo(f'{u.id}: {u.name} {u.points}')


@app.cli.command("gettasks")
@click.argument("userid")
def cli_gettasks(userid):
    tasks = get_task_history(userid)
    click.echo(f'Found {len(tasks)} tasks.')
    for t in tasks:
        click.echo(json.dumps(t.as_dict()))


@app.cli.command("getquestions")
def cli_getquestions():
    qns = get_all_questions()
    print(qns)


@app.cli.command("gettasktemplates")
def cli_gettasktemplates():
    tts = TaskTemplate.query.all()
    click.echo(f'Found {len(tts)} task templates.')
    for t in tts:
        click.echo(f'{t.id}: {t.desc}')


@app.cli.command("getresponses")
@click.argument("userid")
def cli_getresponses(userid):
    resps = QuestionnaireResponse.query.filter(
        QuestionnaireResponse.user_id == userid).all()
    click.echo(f'Found {len(resps)} qn responses.')
    for r in resps:
        click.echo(f'{r.id}: qn_id = {r.question_id}')
        click.echo(f'{r.answer1}')
        click.echo(f'{r.answer2}')


def get_next_tasks(userid):
    return recommend_tasks(get_all_questions(), get_questionnaire_responses(userid), get_all_task_templates(
    ), get_incomplete_tasks(userid), get_completed_tasks(userid))


@app.cli.command("recommend")
@click.argument("userid")
def cli_recommend(userid):
    tasks = get_next_tasks(userid)
    print(tasks)

############################
### FAKE DATA GENERATION ###
############################


def create_questions():
    qns = [("Do you recycle at least 50% of recyclable products you use?", "no", "How hard would it be for you to do that?"),
           ("Do you bring a bag to the supermarket?", "no",
            "How difficult would it be for you to bring one?"),
           ("Do you eat meat?", "yes",
            "How challenging would it be for you to stop eating meat for a while?"),
           ("Do you fly more than twice a year?", "yes",
            "How difficult would it be for you to fly less?"),
           ("Do you avoid single-use food and drink containers and utensils?", "no",
            "Would that be hard for you?"),
           ("Do you drink milk?", "yes", "How difficult would it be for you to switch to plant milk?")]

    for d1, sqo, d2 in qns:
        q = Question(qn1=d1, qn2=d2, subquestion_option=sqo)
        db.session.add(q)
    db.session.commit()


def create_task_templates():
    tasks = []
    tasks.append(TaskTemplate(
        desc="Recycle 4 items",
        user_points=10,
        carbon_savings=0.43,
        waste_savings=0.40,
        max_completions=4
    ))
    tasks.append(TaskTemplate(
        desc="Bring a bag to the supermarket twice",
        user_points=10,
        carbon_savings=0.20,
        waste_savings=0.20,
        max_completions=2
    ))
    tasks.append(TaskTemplate(
        desc="Don't eat meat for a day",
        user_points=10,
        carbon_savings=2.60,
        waste_savings=0.00,
        max_completions=1
    ))
    tasks.append(TaskTemplate(
        desc="Choose a flight that emits less carbon emissions",
        user_points=10,
        carbon_savings=25.00,
        waste_savings=0.00,
        max_completions=1
    ))
    tasks.append(TaskTemplate(
        desc="Decline using a single-use food or drink container or utensil once",
        user_points=10,
        carbon_savings=2.13,
        waste_savings=0.10,
        max_completions=1
    ))
    tasks.append(TaskTemplate(
        desc="Buy a carton of plant milk",
        user_points=10,
        carbon_savings=1.70,
        waste_savings=0.00,
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
    print(f'Creating fake questionnaire responses for userid {userid}')
    r = QuestionnaireResponse(
        user_id=userid,
        question_id=1,
        answer1="yes",
        answer2=""
    )
    db.session.add(r)
    r = QuestionnaireResponse(
        user_id=userid,
        question_id=2,
        answer1="no",
        answer2="2"
    )
    db.session.add(r)
    r = QuestionnaireResponse(
        user_id=userid,
        question_id=3,
        answer1="yes",
        answer2="5"
    )
    db.session.add(r)
    r = QuestionnaireResponse(
        user_id=userid,
        question_id=4,
        answer1="yes",
        answer2="5"
    )
    db.session.add(r)
    r = QuestionnaireResponse(
        user_id=userid,
        question_id=5,
        answer1="no",
        answer2="4"
    )
    db.session.add(r)
    r = QuestionnaireResponse(
        user_id=userid,
        question_id=6,
        answer1="no",
        answer2=""
    )
    db.session.add(r)
    db.session.commit()


###############################################

@app.route('/')
def root():
    response = "Nothing here, move along."
    return response


@app.route('/questionnaire', methods=['POST', 'GET'])
def questionnaire():
    if request.method == 'POST':
        request_data = request.get_json()
        userid = request_data["userId"]

        for row in request_data["results"]:
            ans1, ans2 = "", ""
            if "answer1" in row:
                ans1 = row["answer1"]
            if "answer2" in row:
                ans2 = row["answer2"]
            ans = QuestionnaireResponse(
                user_id=userid,
                question_id=row["questionId"],
                answer1=ans1,
                answer2=ans2
            )
            db.session.add(ans)
        db.session.commit()

        # Debug
        pp.pprint(request_data)
        response = "POSTED"

        # Get next task
        tasks = get_next_tasks(userid)
        task_objects = []
        for tasktemplate in tasks:
            t = Task(
                template_id=tasktemplate.id,
                completed=False,
                user_id=userid,
                num_completions=0
            )
            task_objects.append(t.as_dict())
            db.session.add(t)
        db.session.commit()

        print(f'{len(tasks)} tasks were generated for userid {userid}')

        response = app.response_class(
            response=json.dumps(task_objects),
            status=200,
            mimetype='application/json'
        )

    else:  # GET
        qns = Question.query.all()
        qns = [q.as_dict() for q in qns]
        response = app.response_class(
            response=json.dumps(qns),
            status=200,
            mimetype='application/json'
        )
    return response


@app.route('/user/<int:id>/incompletetasks', methods=['GET'])
def incompletetasks(id):
    tasks = get_incomplete_tasks(id)
    tasks = [t.as_dict() for t in tasks]
    tts = get_all_task_templates()
    tts = [t.as_dict() for t in tts]
    response = app.response_class(
        response=json.dumps({"tasks": tasks, "templates": tts}),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/task/<int:taskid>', methods=['GET', 'POST'])
def task(taskid):
    if request.method == 'POST':
        request_data = request.get_json()
        userid = request_data["userId"]
        taskid = request_data["task"]["id"]
        update = request_data["task"]["update"]
        print(update)

        if update == "yes":
            task = db.session.query(Task).get(taskid)
            print(f'task id = {task.id}')
            template = get_template(task.template_id)
            print(task.num_completions)
            task.num_completions += 1
            print(task.num_completions)
            if task.num_completions == template.max_completions:
                task.completed = True

            user = db.session.query(User).get(userid)
            pts = template.user_points
            user.points += pts

            if task.completed:  # Generate new recommendations
                tasks = get_next_tasks(userid)
                task_objects = []
                for tasktemplate in tasks:
                    t = Task(
                        template_id=tasktemplate.id,
                        completed=False,
                        user_id=userid,
                        num_completions=0
                    )
                    task_objects.append(t.as_dict())
                    db.session.add(t)
                print(f'{len(tasks)} tasks were generated for userid {userid}')
                resp_payload = json.dumps(task_objects)
            else:
                resp_payload = {}
            db.session.commit()

            response = app.response_class(
                response=resp_payload,
                status=200,
                mimetype='application/json'
            )
        else:
            response = app.response_class(
                response="{}",
                status=200,
                mimetype='application/json'
            )
        return response
    else:
        task = get_task(taskid)
        # if task.user_id != userid:
        #     abort(401)
        tts = get_all_task_templates()
        tts = [t.as_dict() for t in tts]
        response = app.response_class(
            response=json.dumps({"task": task.as_dict(), "templates": tts}),
            status=200,
            mimetype='application/json'
        )
        return response


@app.route('/usercallback', methods=['POST'])
def usercallback():
    request_data = request.get_json()
    sub = request_data["sub"]
    user = User.query.filter(User.sub == sub).all()
    if len(user) == 0:
        # No user found, create
        user = User(
            name=request_data["name"],
            points=0,
            sub=sub
        )
        db.session.add(user)
        db.session.commit()
        response = app.response_class(
            response=json.dumps({
                "status": "new",
                "questionnaire_status": "incomplete",
                "user_object": user.as_dict()
            }),
            status=200,
            mimetype='application/json'
        )
        return response
    else:
        # User found
        user = user[0]
        if len(get_questionnaire_responses(user.id)) == 0:
            qstatus = "incomplete"
        else:
            qstatus = "done"
        response = app.response_class(
            response=json.dumps({
                "status": "existing",
                "questionnaire_status": qstatus,
                "user_object": user.as_dict()
            }),
            status=200,
            mimetype='application/json'
        )
        return response
