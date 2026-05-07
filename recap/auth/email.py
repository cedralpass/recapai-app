from flask import render_template
from flask_mail import Message

from recap import Config, mail
from recap.email import send_email
from recap.models import User


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        "[Recap AI] Reset Your Password",
        sender=Config.MAIL_DEFUALT_FROM,
        recipients=[user.email],  # TODO: fix email for recipitent once AWS approves us.
        text_body=render_template("email/reset_password.txt", user=user, token=token),
        html_body=render_template("email/reset_password.html", user=user, token=token),
    )
