# 生产者
from celery_tasks.main import app
from libs.yuntongxun.sms import CCP


# 任务
@app.task
def celery_send_sms_code(mobile, code):
    CCP().send_template_sms(mobile, [code, 5], 1)
