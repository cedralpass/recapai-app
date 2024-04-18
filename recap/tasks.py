import time
from rq import get_current_job
from recap import create_app
import json
from recap.models import User
from flask_mail import Mail, Message
from recap.email import send_password_reset_email 
from recap.config import Config

app = create_app()
app.app_context().push()
app.config['SERVER_NAME'] = Config.TASK_SERVER_NAME


#sample task
def example(seconds=20):
    app.logger.info("Running example Task for seconds %s ", seconds)
    job = get_current_job()
    print('Starting task')
    for i in range(seconds):
        job.meta['progress'] = 100.0 * i / seconds
        job.save_meta()
        print(i)
        time.sleep(1)
    job.meta['progress'] = 100
    job.save_meta()
    print('Task completed')

def send_password_reset_email_task(user_id):
    app.app_context().push()
    user = User.query.get(user_id)
    send_password_reset_email(user)