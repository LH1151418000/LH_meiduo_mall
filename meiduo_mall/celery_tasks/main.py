# 下载并导入celery包
from celery import Celery
import os


if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'


# 创建celery实例对象
celery_app = Celery('meiduo')
# 获取redis路径
celery_app.config_from_object('celery_tasks.config')
# 发现任务
celery_app.autodiscover_tasks(['celery_tasks.sms',
                               'celery_tasks.email',
                               'celery_tasks.html'
                               ])
