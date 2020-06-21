from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django_redis import get_redis_connection
from meiduo_mall.libs.captcha.captcha import captcha
from django.views import View
# from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from random import randint
import logging
from celery_tasks.sms.tasks import ccp_send_sms_code


logger = logging.getLogger('django')


# Create your views here.


class ImageCodeView(View):
    def get(self, request, uuid):
        text, image = captcha.generate_captcha()
        print(text)
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex('image_%s' % uuid, 300, text)
        return HttpResponse(image, content_type='image/jpg')


class SMSCodeView(View):
    def get(self, request, mobile):

        redis_conn = get_redis_connection('verify_code')

        sms_flag = redis_conn.get('sms_flag_%s' % mobile)
        if sms_flag:
            return JsonResponse({'code': 404, 'errmsg': '发送短信过于频繁'})

        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        if not all([image_code_client, uuid]):
            return JsonResponse({'code': 404, 'errmsg': '缺少必传参数'})

        image_code_server = redis_conn.get('image_%s' % uuid)
        if not image_code_server:
            return JsonResponse({'code': 404, 'errmsg': '验证码已失效'})

        image_code_server = image_code_server.decode()
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logger.error(e)

        if image_code_server.lower() != image_code_client.lower():
            return JsonResponse({'code': 404, 'errmsg': '验证码错误'})

        sms_code = '%06d' % randint(0, 999999)
        print(sms_code)
        pl = redis_conn.pipeline()

        redis_conn.setex('sms_%s' % mobile, 300, sms_code)
        redis_conn.setex('sms_flag_%s' % mobile, 60, 1)

        pl.execute()

        # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        ccp_send_sms_code.delay(mobile, sms_code)

        return JsonResponse({'code': 0, 'errmsg': '发送成功'})
