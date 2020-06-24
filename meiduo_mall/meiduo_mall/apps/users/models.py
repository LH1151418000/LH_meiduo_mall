from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from itsdangerous import TimedJSONWebSignatureSerializer, BadData
from django.conf import settings


# 我们重写用户模型类, 继承自 AbstractUser
class User(AbstractUser):
    """自定义用户模型类"""

    # 额外增加 mobile 字段
    mobile = models.CharField(max_length=11,
                              unique=True,
                              verbose_name='手机号')

    # 增加 email 字段
    email_active = models.BooleanField(default=False,
                                       verbose_name='邮箱验证状态')

    # 对当前表进行相关设置:
    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    # 在 str 魔法方法中, 返回用户名称
    def __str__(self):
        return self.username

    def generate_verify_email_url(self):
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                     expires_in=3600 * 24)

        data = {'user_id': self.id, 'email': self.email}

        token = serializer.dumps(data).decode()

        verify_url = settings.EMAIL_VERIFY_URL + token

        return verify_url

    @staticmethod
    def check_verify_email_token(token):

        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                                     expires_in=3600 * 24)

        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            user_id = data.get('user_id')
            email = data.get('email')

        try:
            user = User.objects.get(id=user_id,
                                    email=email)
        except User.DoesNotExist:
            return None
        else:
            return user
