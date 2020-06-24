from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django_redis import get_redis_connection
from meiduo_mall.libs.captcha.captcha import captcha
from django.views import View
# from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from random import randint
import logging
from celery_tasks.sms.tasks import ccp_send_sms_code

"""
HttpResponse
    (content=响应体, content_type=响应体数据类型, status=状态码)
    : 用户可以修改返回到数据类型，适用于返回图片、视频、音频等二进制文件
        
JsonResponse
    : JsonResponse是HttpResponse子类
    : 适用于json数据返回，但是不能返回模板
"""

logger = logging.getLogger('django')


# Create your views here.

# 图形验证码
class ImageCodeView(View):
    def get(self, request, uuid):
        # 利用captcha生成验证码 text:文字验证码 image:图形验证码
        text, image = captcha.generate_captcha()
        print(text)
        # 获取redis数据库对象
        redis_conn = get_redis_connection('verify_code')
        # 写入redis数据库并设置过期时间
        redis_conn.setex('image_%s' % uuid, 300, text)
        # 返回验证码图片
        return HttpResponse(image, content_type='image/jpg')


# 短信验证码
class SMSCodeView(View):
    def get(self, request, mobile):
        # 获取redis对象
        redis_conn = get_redis_connection('verify_code')
        # 获取redis中设置的判断
        # 用于判断用户是否中60秒内重复发送短信
        sms_flag = redis_conn.get('sms_flag_%s' % mobile)
        if sms_flag:
            return JsonResponse({'code': 404, 'errmsg': '发送短信过于频繁'})

        # 获取用户输入的图形验证码
        image_code_client = request.GET.get('image_code')
        # 获取该图形验证码的uuid
        uuid = request.GET.get('image_code_id')

        # 判断用户是否输入
        if not all([image_code_client, uuid]):
            return JsonResponse({'code': 404, 'errmsg': '缺少必传参数'})

        # 获取redis中的图形验证码用于与用户的进行对比
        image_code_server = redis_conn.get('image_%s' % uuid)
        # 判断uuid是否过期
        if not image_code_server:
            return JsonResponse({'code': 404, 'errmsg': '验证码已失效'})

        # 对获取的验证码进行解码成字符串
        image_code_server = image_code_server.decode()
        try:
            # 获取图形验证码后进行删除
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logger.error(e)

        # 设置小写后，进行图形验证码对比
        if image_code_server.lower() != image_code_client.lower():
            return JsonResponse({'code': 404, 'errmsg': '验证码错误'})

        # 生成6位数短信验证码
        sms_code = '%06d' % randint(0, 999999)
        print(sms_code)

        # 设置管道，提高效率，减少握手次数
        pl = redis_conn.pipeline()
        redis_conn.setex('sms_%s' % mobile, 300, sms_code)
        redis_conn.setex('sms_flag_%s' % mobile, 60, 1)
        # 执行管道
        pl.execute()

        # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        # 使用了celery程序进行发送短信---'异步'
        ccp_send_sms_code.delay(mobile, sms_code)

        return JsonResponse({'code': 0, 'errmsg': '发送成功'})
