# 导入创建的实例对象
from celery_tasks.main import celery_app
# 导入云通讯发送方法
from celery_tasks.yuntongxun.ccp_sms import CCP


# 使用实例对象装饰发送函数
@celery_app.task(name='tasks_send')
def ccp_send_sms_code(mobile, sms_code):
    result = CCP().send_template_sms(mobile, [sms_code, 5], 1)
    return result
