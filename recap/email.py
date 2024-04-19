from flask_mail import Message
from flask import render_template
from recap import mail,Config
from recap.models import User

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

