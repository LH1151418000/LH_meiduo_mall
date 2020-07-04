from django.shortcuts import render
from django.views import View
from alipay import AliPay
from django.conf import settings
from orders.models import *
from django.http import JsonResponse
from . models import Payment
import os

# Create your views here.

class PaymentStatusView(View):

    def put(self, request):
        # 提取支付宝查询参数
        query_string = request.GET  # QueryDict
        # {'out_trade_no': xxx, 'trade_no': xxx, 'sign': xxx}
        query_dict = query_string.dict()  # QueryDict.dict() 转化为普通字典
        # 获取支付宝签名，用来验证数据真伪
        signature = query_dict.pop('sign')

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_public_key.pem'),
            sign_type='RSA2',
            debug=settings.ALIPAY_DEBUG
        )

        # 校验参数是否伪造
        success = alipay.verify(query_dict, signature)
        if success:
            out_trade_no = query_dict.get('out_trade_no')  # 美多订单号
            trade_no = query_dict.get('trade_no')  # 支付宝订单号
            Payment.objects.create(
                order_id=out_trade_no,
                trade_id=trade_no
            )

            order = OrderInfo.objects.get(pk=out_trade_no)
            order.status = OrderInfo.ORDER_STATUS_ENUM['UNSEND']
            order.save()

            return JsonResponse({'code': 0, 'errmsg': 'ok', 'trade_id': trade_no})
        return JsonResponse({'code': 400, 'errmsg': '支付失败'})


class PaymentView(View):

    def get(self, request, order_id):
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,
            app_private_key_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            alipay_public_key_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'keys/app_public_key.pem'),
            sign_type='RSA2',
            debug=settings.ALIPAY_DEBUG
        )

        order = OrderInfo.objects.get(pk=order_id)
        query_string = alipay.api_alipay_trade_page_pay(
            # 付款主题
            subject='美多商场订单：%s' % order_id,
            # 美多商场的订单号
            out_trade_no=str(order_id),
            # 订单总价
            total_amount=float(order.total_amount),
            # 付款后重定向回美多链接
            return_url=settings.ALIPAY_RETURN_URL
        )

        alipay_url = settings.ALIPAY_URL + '?' + query_string

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'alipay_url': alipay_url})
