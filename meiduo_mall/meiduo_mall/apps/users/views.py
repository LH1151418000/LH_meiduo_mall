import json
import logging
import re

from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User, Address
from celery_tasks.email.tasks import send_verify_email
from goods.models import SKU

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


class CreateAddressView(View):
    def post(self, request):
        try:
            count = Address.objects.filter(user=request.user, is_deleted=False).count()
        except Exception as e:
            return JsonResponse({'code': 400, 'errmsg': '获取地址数据出错'})

        if count > 20:
            return JsonResponse({'code': 400, 'errmsg': '地址超出上限'})

        json_dict = json.loads(request.body)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({'code': 400, 'errmsg': '缺少必传参数'})

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400, 'errmsg': '参数mobile有误'})

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({'code': 400, 'errmsg': '参数tel有误'})
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({'code': 400, 'errmsg': '参数email有误'})

        # 保存地址信息
        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            # 设置默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()
        except Exception as e:
            return JsonResponse({'code': 400, 'errmsg': '新增地址失败'})

        # 新增地址成功，将新增的地址响应给前端实现局部刷新
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'address': address_dict})


class AddressView(View):
    """用户收货地址"""

    def get(self, request):
        """提供地址管理界面
        """
        # 获取所有的地址:
        addresses = Address.objects.filter(user=request.user,
                                           is_deleted=False)

        # 创建空的列表
        address_dict_list = []
        # 遍历
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }

            # 将默认地址移动到最前面
            default_address = request.user.default_address
            if default_address.id == address.id:
                # 查询集 addresses 没有 insert 方法
                address_dict_list.insert(0, address_dict)
            else:
                address_dict_list.append(address_dict)

        default_id = request.user.default_address_id

        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'addresses': address_dict_list,
                             'default_address_id': default_id})


class UpdateDestroyAddressView(View):
    """修改和删除地址"""

    def put(self, request, address_id):
        """修改地址"""
        # 接收参数
        json_dict = json.loads(request.body)
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '参数mobile有误'})

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数tel有误'})
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数email有误'})

        # 判断地址是否存在,并更新地址信息
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400,
                                 'errmsg': '更新地址失败'})

        # 构造响应数据
        address = Address.objects.get(id=address_id)
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 响应更新地址结果
        return JsonResponse({'code': 0,
                             'errmsg': '更新地址成功',
                             'address': address_dict})

    def delete(self, request, address_id):
        """删除地址"""
        try:
            # 查询要删除的地址
            address = Address.objects.get(id=address_id)

            # 将地址逻辑删除设置为True
            address.is_deleted = True
            address.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400,
                                 'errmsg': '删除地址失败'})

        # 响应删除地址结果
        return JsonResponse({'code': 0,
                             'errmsg': '删除地址成功'})


class DefaultAddressView(View):
    """设置默认地址"""

    def put(self, request, address_id):
        """设置默认地址"""
        try:
            # 接收参数,查询地址
            address = Address.objects.get(id=address_id)

            # 设置地址为默认地址
            request.user.default_address = address
            request.user.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400,
                                 'errmsg': '设置默认地址失败'})

        # 响应设置默认地址结果
        return JsonResponse({'code': 0,
                             'errmsg': '设置默认地址成功'})


class UpdateTitleAddressView(View):
    """设置地址标题"""

    def put(self, request, address_id):
        """设置地址标题"""
        # 接收参数：地址标题
        json_dict = json.loads(request.body)
        title = json_dict.get('title')

        try:
            # 查询地址
            address = Address.objects.get(id=address_id)

            # 设置新的地址标题
            address.title = title
            address.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400,
                                 'errmsg': '设置地址标题失败'})

        # 4.响应删除地址结果
        return JsonResponse({'code': 0,
                             'errmsg': '设置地址标题成功'})


class ChangePasswordView(LoginRequiredMixin, View):
    """修改密码"""

    def put(self, request):
        """实现修改密码逻辑"""
        # 接收参数
        dict = json.loads(request.body)
        old_password = dict.get('old_password')
        new_password = dict.get('new_password')
        new_password2 = dict.get('new_password2')

        # 校验参数
        if not all([old_password, new_password, new_password2]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})

        result = request.user.check_password(old_password)
        if not result:
            return JsonResponse({'code': 400,
                                 'errmsg': '原始密码不正确'})

        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_password):
            return JsonResponse({'code': 400,
                                 'errmsg': '密码最少8位,最长20位'})

        if new_password != new_password2:
            return JsonResponse({'code': 400,
                                 'errmsg': '两次输入密码不一致'})

        # 修改密码
        try:
            request.user.set_password(new_password)
            request.user.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400,
                                 'errmsg': '修改密码失败'})

        # 清理状态保持信息
        logout(request)

        response = JsonResponse({'code': 0,
                                 'errmsg': 'ok'})

        response.delete_cookie('username')

        # # 响应密码修改结果：重定向到登录界面
        return response


class UserBrowseHistory(LoginRequiredMixin, View):

    def post(self, request):
        json_dict = json.loads(request.body)
        try:
            sku_id = json_dict.get('sku_id')
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '商品不存在'})
        SKU.objects.get(id=sku_id)

        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id
        pl.lrem('history_%s' % user_id, 0, sku_id)
        pl.lpush('history_%s' % user_id, sku_id)
        pl.ltrim('history_%s' % user_id, 0, 4)
        pl.execute()

        return JsonResponse({'code': 0, 'errmsg': 'ok'})

    def get(self, request):
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image_url,
                'price': sku.price
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'skus': skus
        })
