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
from datetime import datetime, timezone
import sqlalchemy as sa

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
    app.logger.debug('inside classify_url')
    classify_result=None
    try:
      #find article by url_ref for user 
      app.logger.debug("finding article to classify for %s", url)
      article = Article.get_article_by_url_path(url,user_id)
      print(article)
      #classify artitle using  AiAPIHelper
      classify_result = AiApiHelper.ClassifyUrl(url, user_id) #TODO : should be the article id, but using user-id for now
      #save resutls to article found
      app.logger.debug("saving results to article")
      app.logger.debug(classify_result['summary'])
      save_classification_result(classify_result, article)
      app.logger.debug("saving article")
      db.session.add(article)
      db.session.commit()
      app.logger.debug("article saved")
    except Exception as e:
      app.logger.debug("Error in Classification Service: %s", e)
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
    # set classified to datetime now in utc timezone
    article.classified = datetime.now(timezone.utc)


def organize_taxonomy_task(user_id):
    from recap.taxonomy_helpers import build_rich_organize_context
    app.logger.info('organize_taxonomy_task starting for user_id=%s', user_id)

    context_string = build_rich_organize_context(user_id)

    PROMPT = (
        "Can you recommend a consolidated category list? "
        "Merge similar or related categories, especially small ones with 1-3 articles. "
        "Keep category names concise and understandable to a human reader."
    )
    FORMAT = (
        "Respond with JSON in this exact structure:\n"
        "{\n"
        '  "description": "A concise summary of the changes made.",\n'
        '  "mappings": [\n'
        '    {"new_category": "New Name", "old_category": "Old Name"},\n'
        '    {"new_category": "New Name", "old_category": "Old Name"}\n'
        "  ]\n"
        "}"
    )

    json_response = AiApiHelper.PerformTask(context_string, PROMPT, FORMAT, user_id)
    app.logger.info('organize_taxonomy_task AI response keys: %s', list(json_response.keys()) if json_response else 'empty')

    if not json_response or 'mappings' not in json_response:
        raise RuntimeError('AI did not return a usable taxonomy response — mappings key missing')

    job = get_current_job()
    app.redis.setex(f'taxonomy:organize:{job.id}', 3600, json.dumps(json_response))


def suggest_splits_task(user_id, threshold=12):
    from recap.taxonomy_helpers import build_split_context
    app.logger.info('suggest_splits_task starting for user_id=%s threshold=%s', user_id, threshold)

    job = get_current_job()

    rows = db.session.execute(
        sa.select(Article.category, sa.func.count(Article.id).label('cnt'))
        .where(Article.user_id == user_id)
        .where(Article.classified.isnot(None))
        .group_by(Article.category)
        .having(sa.func.count(Article.id) >= threshold)
        .order_by(sa.func.count(Article.id).desc())
    ).all()
    large_categories = [(cat, cnt) for cat, cnt in rows if cat]

    if not large_categories:
        app.redis.setex(f'taxonomy:splits:{job.id}', 3600, json.dumps({}))
        return

    SPLIT_PROMPT = (
        "Split these articles into 2-4 distinct, meaningful groups based on their themes. "
        "Name each group clearly (2-4 words). "
        "Assign every article to exactly one group."
    )
    SPLIT_FORMAT = (
        'Respond with JSON in this exact structure:\n'
        '{\n'
        '  "description": "Brief rationale for the groupings",\n'
        '  "assignments": [\n'
        '    {"article_id": 42, "new_category": "Group Name"},\n'
        '    {"article_id": 43, "new_category": "Group Name"}\n'
        '  ]\n'
        '}'
    )

    total = len(large_categories)
    suggestions = {}

    for done, (category_name, count) in enumerate(large_categories):
        article_rows = db.session.execute(
            sa.select(Article.id, Article.title, Article.sub_categories)
            .where(Article.user_id == user_id)
            .where(Article.category == category_name)
            .order_by(Article.id)
        ).all()

        context = build_split_context(category_name, article_rows)
        result = AiApiHelper.PerformTask(context, SPLIT_PROMPT, SPLIT_FORMAT, user_id)

        if result and 'assignments' in result:
            assignments = {
                str(a['article_id']): a['new_category']
                for a in result['assignments']
                if 'article_id' in a and 'new_category' in a
            }
            sub_counts = {}
            for new_cat in assignments.values():
                sub_counts[new_cat] = sub_counts.get(new_cat, 0) + 1

            suggestions[category_name] = {
                'original_count': count,
                'description': result.get('description', ''),
                'assignments': assignments,
                'sub_counts': sorted(sub_counts.items(), key=lambda x: x[1], reverse=True),
            }

        job.meta['progress'] = f"{done + 1} of {total} categories processed"
        job.save_meta()

    app.redis.setex(f'taxonomy:splits:{job.id}', 3600, json.dumps(suggestions))


def ping_aiapi():
    import urllib.request
    url = Config.RECAP_AI_API_URL.rstrip('/') + '/hello'
    try:
        urllib.request.urlopen(url, timeout=30)
        app.logger.info('ping_aiapi: AI API is awake')
    except Exception as e:
        app.logger.warning('ping_aiapi: request failed: %s', e)

