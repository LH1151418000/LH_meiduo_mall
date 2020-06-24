from django.views import View
import json
import re

from QQLoginTool.QQtool import OAuthQQ
from django import http
from django.conf import settings
from django.views import View
from django_redis import get_redis_connection
from .utils import check_access_token
from users.models import User
from django.db import DatabaseError
from django.contrib.auth import login
from oauth.models import OAuthQQUser
from oauth.utils import generate_access_token
# Create your views here.


class QQURLView(View):
    def get(self, request):
        next = request.GET.get('next')

        oauth = OAuthQQ(
            client_id=settings.QQ_CLIENT_ID,
            client_secret=settings.QQ_CLIENT_SECRET,
            redirect_uri=settings.QQ_REDIRECT_URI,
            state=next
        )
        login_url = oauth.get_qq_url()

        return http.JsonResponse({'code': 0, 'errmsg': 'ok', 'login_url': login_url})


class QQUserView(View):
    def get(self, request):
        code = request.GET.get('code')

        if not code:
            return http.JsonResponse({'code': 400, 'errmsg': '缺少code'})

        oauth = OAuthQQ(
            client_id=settings.QQ_CLIENT_ID,
            client_secret=settings.QQ_CLIENT_SECRET,
            redirect_uri=settings.QQ_REDIRECT_URI
        )

        try:
            access_token = oauth.get_access_token(code)
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            return http.JsonResponse({'code': 400, 'errmsg': 'oauth2.0认证失败, 即获取qq信息失败'})

        try:
            qq_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            token = generate_access_token(openid)
            return http.JsonResponse({'code': 400, 'errmsg': '用户未绑定', 'access_token': token})
        else:
            user = qq_user.user

            login(request, user)

            response = http.JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('username', user.username, max_age=3600 * 24 * 14)
            return response

    def post(self, request):

        dict = json.loads(request.body)
        mobile = dict.get('mobile')
        password = dict.get('password')
        sms_code_client = dict.get('sms_code')
        access_token = dict.get('access_token')

        if not all([mobile, password, sms_code_client]):
            return http.JsonResponse({'code': 400, 'errmsg': '缺少必传参数'})

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.JsonResponse({'code': 400, 'errmsg': '请输入正确的手机号码'})

        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.JsonResponse({'code': 400, 'errmsg': '请输入8-20位的密码'})

        redis_conn = get_redis_connection('verify_code')

        sms_code_server = redis_conn.get('sms_%s' % mobile)

        if sms_code_server is None:
            return http.JsonResponse({'code': 400, 'errmsg': '验证码失效'})

        if sms_code_client != sms_code_server.decode():
            return http.JsonResponse({'code': 400, 'errmsg': '验证码输入有误'})

        openid = check_access_token(access_token)
        if not openid:
            return http.JsonResponse({'code': 400, 'errmsg': '缺少openid'})

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username=mobile,
                                            password=password,
                                            mobile=mobile)
        else:
            if not user.check_password(password):
                return http.JsonResponse({'code': 400, 'errmsg': '密码错误'})

        try:
            OAuthQQUser.objects.create(openid=openid,
                                       user=user)
        except DatabaseError:
            return http.JsonResponse({'code': 400, 'errmsg': '往数据库添加数据失败'})

        login(request, user)

        response = http.JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', user.username, max_age=3600 * 24 * 14)
        return response



