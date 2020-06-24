from celery_tasks.main import celery_app
from django.core.mail import send_mail
from django.conf import settings


@celery_app.task(name='send_verify_email')
def send_verify_email(to_email, verify_url):
    subject = '美多商场邮箱验证'
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用美多商城。</p>' \
                   '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s<a></p>' % (to_email, verify_url, verify_url)

    # send_mail(subject, message, from_email, recipient_list,html_message=None)
    #
    # subject 邮件标题
    # message 普通邮件正文， 普通字符串
    # from_email 发件人
    # recipient_list 收件人列表
    # html_message 多媒体邮件正文，可以是html字符串

    result = send_mail(subject,  # 邮件标题
                       "",  # 普通邮件正文，普通字符串
                       settings.EMAIL_FROM,  # 发件人
                       [to_email],  # 收件人列表
                       html_message=html_message)  # 多媒体邮件正文，可以是html字符串
    return result
