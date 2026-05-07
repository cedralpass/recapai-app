from flask import render_template
from flask_mail import Message

from recap import Config, mail
from recap.models import User


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    send_result = mail.send(msg)
    return send_result
