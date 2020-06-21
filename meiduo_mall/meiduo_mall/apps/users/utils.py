from .models import User
from django.contrib.auth.backends import ModelBackend
import re


def get_user_by_account(account):
    try:
        if re.match(r'1[3-9]\d{9}', account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist as e:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        重写认证方法，实现用户名和mobile登录功能
        :param request: 请求对象
        :param username: 用户名
        :param password: 密码
        :param kwargs: 其他参数
        :return: user
        """

        user = get_user_by_account(username)
        if user and user.check_password(password):
            return user
