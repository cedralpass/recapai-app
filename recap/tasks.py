import time
from rq import get_current_job
from recap import create_app
import json
from recap.models import User, Article
from flask_mail import Mail, Message
from recap.auth.email import send_password_reset_email 
from recap.config import Config
from recap.aiapi_helper import AiApiHelper
from recap import db  

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

def classify_url(url, user_id):
    print('inside classify_url')
    classify_result=None

    try:
      #find article by url_ref for user 
      print("finding article")
      article = Article.get_article_by_url_path(url,user_id)
      print(article)
      #classify artitle using  AiAPIHelper
      classify_result = AiApiHelper.ClassifyUrl(url, user_id) #TODO : should be the article id, but using user-id for now
      #save resutls to article found
      print("saving results to article")
      print(classify_result['summary'])
      save_classification_result(classify_result, article)
      print("saving article")
      db.session.add(article)
      db.session.commit()
      print("article saved")
    except Exception as e:
      print("Error in Classification Service: %s", e)
    return classify_result

def save_classification_result(classify_result, article):
    article.summary=classify_result['summary']
    article.title=classify_result['blog_title']
    article.author_name = classify_result['author']
    article.category = classify_result['category']
    if 'key_topics' not in classify_result.keys():
        classify_result['key_topics'] = []
    if 'sub_categories' not in classify_result.keys():
        classify_result['sub_categories'] = []
    article.key_topics = json.dumps(classify_result['key_topics'])
    article.sub_categories = json.dumps(classify_result['sub_categories'])
    
    
