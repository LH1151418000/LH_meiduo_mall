from .models import User
from django.contrib.auth.backends import ModelBackend
import re


# 设置一个判断，用户判断用户输入的是手机号还是用户名
def get_user_by_account(account):
    try:
        # 判断输入值是否符合此正则
        if re.match(r'1[3-9]\d{9}', account):
            # 符合，使用User获取数据库中对应值
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist as e:
        # 如果未获取到值返回None
        return None
    else:
        # 获取到返回user
        return user


# 定义一个类继承ModelBackend
class UsernameMobileAuthBackend(ModelBackend):
    # 重写authenticate函数
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        重写认证方法，实现用户名和mobile登录功能
        :param request: 请求对象
        :param username: 用户名
        :param password: 密码
        :param kwargs: 其他参数
        :return: user
        """
        # 调用上面函数
        user = get_user_by_account(username)
        # 利用Django自带判断，判断用户名密码是否正确
        if user and user.check_password(password):
            # 正确则返回user 否则返回None
            return user
