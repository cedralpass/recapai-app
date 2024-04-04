import time
from rq import get_current_job
from recap import create_app
import json

app = create_app()
app.app_context().push()

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