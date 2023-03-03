# celery启动文件
# celery -A celery_tasks.main worker -l info -P eventlet 启用任务(虚拟环境下输入)
import os

from celery import Celery

# 配置django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings')
# 创建celery实例
app = Celery('celery_tasks')
# 加载celery配置
app.config_from_object('celery_tasks.config')
# 自动注册celery任务
app.autodiscover_tasks(['celery_tasks.sms'])
