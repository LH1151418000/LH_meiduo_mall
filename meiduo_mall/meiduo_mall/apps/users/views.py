import json
import logging
import re

from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User
from celery_tasks.email.tasks import send_verify_email
# 设置log日志
logger = logging.getLogger('django')


# Create your views here.

# 用户名重复注册
class UserCountView(View):
    def get(self, request, username):
        try:
            # 使用重写后的User类查询数据库中username，并查询数据库中是否有数据
            count = User.objects.filter(username=username).count()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 404, 'errmsg': '无法访问数据库'})
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})


# 手机号重复注册
class MobileCountView(View):
    def get(self, request, mobile):
        try:
            # 查询数据库中手机号个数
            count = User.objects.filter(mobile=mobile).count()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 404, 'errmsg': '无法访问数据库'})
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})


# 用户注册逻辑
class RegisterView(View):
    def post(self, request):
        # 获取用户输入，原是byt数据，因是Django2.2.5故不需要对byt数据进行解码
        data = json.loads(request.body)  # .decode()
        username = data.get('username')
        password = data.get('password')
        password2 = data.get('password2')
        mobile = data.get('mobile')
        sms_code = data.get('sms_code')
        allow = data.get('allow')

        # 判断用户是否输入
        if not all([username, password, password2, mobile, sms_code]):
            return JsonResponse({'code': 400, 'errmsg': '缺少必传参数'})

        # 判断用户名格式是否正确
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return JsonResponse({'code': 400, 'errmsg': '用户名格式错误！'})

        # 判断密码格式是否正确
        if not re.match(r'^[a-zA-Z0-9_-]{8,20}$', password):
            return JsonResponse({'code': 400, 'errmsg': '密码格式错误！'})

        # 判断两次密码是否一致
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400, 'errmsg': '手机号格式错误！'})

        # 判断是否勾选
        if not isinstance(allow, bool):
            return JsonResponse({'code': 400, 'errmsg': '协议类型错误！'})

        if allow != True:
            return JsonResponse({'code': 400, 'errmsg': '协议未勾选！'})

        # 定义redis数据库对象
        redis_conn = get_redis_connection('verify_code')

        # 获取redis中对应手机号的短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)  # key

        # 判断是否从redis中获取到数据
        if not sms_code_server:
            return JsonResponse({'code': 400, 'errmsg': '验证码已过期'})

        # 判断用户输入的验证码是否与redis中匹配
        if sms_code != sms_code_server.decode():
            return JsonResponse({'code': 400, 'errmsg': '验证码错误'})

        try:
            # 将用户名、密码、手机号写入mysql
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except User.DoesNotExist as e:
            return JsonResponse({'code': 400, 'errmsg': '存入数据库失败'})

        # 状态保持
        login(request, user)
        # 提前设置响应
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        # 设置cookie，才能状态保持
        response.set_cookie('username', username)

        return response


# 用户登录
class LoginView(View):
    def post(self, request):
        # 获取用户输入
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        remembered = data.get('remembered')

        # 判断用户是否输入必传参数
        if not all([username, password]):
            return JsonResponse({'code': 400, 'errmsg': '缺少必传参数'})

        # 判断用户密码是否正确
        user = authenticate(request, username=username, password=password)

        # 验证无效返回的None
        if user is None:
            return JsonResponse({'code': 400, 'errmsg': '用户名或密码错误'})

        # 状态保持
        login(request, user)

        # 设置session、用户是否点击了'记住密码'
        if not remembered:
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)

        # 设置cookie
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', username)

        return response


# 用户登出
class LogOutView(View):

    def delete(self, request):
        # 获取登出函数，并调用
        logout(request)

        response = JsonResponse({'code': 0, 'errmsg': 'ok'})

        # 删除cookie
        response.delete_cookie('username')
        return response


# 进入用户中心页面
class UserInfoView(LoginRequiredMixin, View):
    """用户中心

    继承于：LoginRequiredMixin
    在父类中进行了判断用户是否登录
    如果登录 进入用户中心页面
    如果未登录 返回用户登录页面
    """

    def get(self, request):
        info_data = {'username': request.user.username,
                     'mobile': request.user.mobile,
                     'email': request.user.email,
                     'email_active': request.user.email_active}
        # 返回前端需要的用户数据 判断是否是此用户登录
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'info_data': info_data})


class EmailView(View):
    def put(self, request):
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            return JsonResponse({'code': 400, 'errmsg': '缺少email'})

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return JsonResponse({'code': 400, 'errmsg': 'email格式错误'})

        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            return JsonResponse({'code': 400, 'errmsg': '添加邮箱失败'})

        verify_url = request.user.generate_verify_email_url()

        send_verify_email(email, verify_url)

        return JsonResponse({'code': 0, 'errmsg': 'ok'})


class VerifyEmailView(View):
    def put(self, request):
        token = request.GET.get('token')

        if not token:
            return JsonResponse({'code': 400, 'errmsg': '缺少token'})

        user = User.check_verify_email_token(token)
        if not user:
            return JsonResponse({'code': 400, 'errmsg': '无效对token'})

        try:
            user.email_active = True
            user.save()
        except Exception:
            return JsonResponse({'code': 400, 'errmsg': '邮件激活失败'})

        return JsonResponse({'code': 0, 'errmsg': 'ok'})
