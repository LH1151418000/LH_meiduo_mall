import json
import logging
import re

from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection

from .models import User

logger = logging.getLogger('django')


# Create your views here.

# class UserCountView(View):
#
#     def get(self, request, username):
#         count = User.objects.filter(username=username).count()
#         return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})
#
#
# class MobileCountView(View):
#
#     def get(self, request, mobile):
#         count = User.objects.filter(mobile=mobile).count()
#         return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})


class UserCountView(View):
    def get(self, request, username):
        try:
            count = User.objects.filter(username=username).count()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 404, 'errmsg': '无法访问数据库'})
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})


class MobileCountView(View):
    def get(self, request, mobile):
        try:
            count = User.objects.filter(mobile=mobile).count()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 404, 'errmsg': '无法访问数据库'})
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})


class RegisterView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        password2 = data.get('password2')
        mobile = data.get('mobile')
        sms_code = data.get('sms_code')
        allow = data.get('allow')

        if not all([username, password, password2, mobile, sms_code]):
            return JsonResponse({'code': 400, 'errmsg': '缺少必传参数'})

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return JsonResponse({'code': 400, 'errmsg': '用户名格式错误！'})

        if not re.match(r'^[a-zA-Z0-9_-]{8,20}$', password):
            return JsonResponse({'code': 400, 'errmsg': '密码格式错误！'})

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400, 'errmsg': '手机号格式错误！'})

        if not isinstance(allow, bool):
            return JsonResponse({'code': 400, 'errmsg': '协议格式错误！'})

        if allow != True:
            return JsonResponse({'code': 400, 'errmsg': '协议未勾选！'})

        redis_conn = get_redis_connection('verify_code')

        sms_code_server = redis_conn.get('sms_%s' % mobile)

        if not sms_code_server:
            return JsonResponse({'code': 400, 'errmsg': '验证码已过期'})

        if sms_code != sms_code_server.decode():
            return JsonResponse({'code': 400, 'errmsg': '验证码错误'})

        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except Exception as e:
            return JsonResponse({'code': 400, 'errmsg': '存入数据库失败'})

        login(request, user)

        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', username)

        return response


class LoginView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        remembered = data.get('remembered')

        if not all([username, password]):
            return JsonResponse({'code': 400, 'errmsg': '缺少必传参数'})

        user = authenticate(username=username, password=password)

        if user is None:
            return JsonResponse({'code': 400, 'errmsg': '用户名或密码错误'})

        login(request, user)

        if not remembered:
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)

        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', username)

        return response
