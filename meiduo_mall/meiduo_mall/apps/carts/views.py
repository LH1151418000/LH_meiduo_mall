import base64
import json
import pickle

from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection
from goods.models import SKU
from .utils import *
# Create your views here.


class CartSelectAllView(View):

    def put(self, request):
        cart_dict = json.loads(request.body)
        selected = cart_dict.get('selected', True)

        if not isinstance(selected, bool):
            return JsonResponse({'code': 400, 'errmsg': '参数错误'})

        if request.user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_cart, redis_selected = get_redis_carts(request)

            sku_ids = redis_cart.keys()
            if selected:
                redis_conn.sadd('selected_%s' % request.user.id, *sku_ids)
            else:
                redis_conn.srem('selected_%s' % request.user.id, *sku_ids)

            return JsonResponse({'code': 0, 'errmsg': 'ok'})
        else:
            cookie_cart = get_carts_from_cookie(request)
            sku_ids = cookie_cart.keys()

            for sku_id in sku_ids:
                cookie_cart[sku_id]['selected'] = selected

            data = get_cookie_cart_data(cookie_cart)

            response = JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('carts', data)
            return response


class CartsView(View):

    def delete(self, request):
        # 1、提取参数
        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')

        if request.user.is_authenticated:
            # 2、已经登陆，删除redis购物车数据
            redis_conn = get_redis_connection('carts')
            redis_conn.hdel('carts_%s' % request.user.id, sku_id)
            redis_conn.srem('selected_%s' % request.user.id, sku_id)
            return JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })
        else:
            cookie_cart = get_carts_from_cookie(request)
            del cookie_cart[sku_id]
            data = get_cookie_cart_data(cookie_cart)
            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })
            response.set_cookie('carts', data)
            return response

    def put(self, request):
        json_dict = json.loads(request.body)

        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        if not all([sku_id, count]):
            return JsonResponse({'code': 0, 'errmsg': '缺少参数!'})
        if isinstance(sku_id, str) and not sku_id.isdigit():
            return JsonResponse({'code': 0, 'errmsg': '参数错误!'})
        if isinstance(count, str) and not count.isdigit():
            return JsonResponse({'code': 400, 'errmsg': '参数错误！'})
        if not isinstance(selected, bool):
            return JsonResponse({'code': 400, 'errmsg': '参数错误！'})

        if request.user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_conn.hset('carts_%s' % request.user.id, sku_id, count)

            if selected:
                redis_conn.sadd('selected_%s' % request.user.id, sku_id)
            else:
                redis_conn.srem('selected_%s' % request.user.id, sku_id)

            return JsonResponse({
                'code': 0,
                'errmsg': 'ok',
                'cart_sku': {
                    'id': sku_id,
                    'count': count,
                    'selected': selected
                }
            })

        else:
            cart_data = get_carts_from_cookie(request)

            cart_data[sku_id]['count'] = count
            cart_data[sku_id]['selected'] = selected

            data = get_cookie_cart_data(cart_data)

            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok',
                'cart_sku': {
                    'id': sku_id,
                    'count': count,
                    'selected': selected
                }
            })

            response.set_cookie('carts', data)
            return response

    def post(self, request):
        # 1、接受参数
        json_dict = json.loads(request.body)
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)
        # 2、校验参数
        if not all([sku_id, count]):
            return JsonResponse({'code': 400, 'errmsg': '缺少参数!'})

        if isinstance(sku_id, str) and not sku_id.isdigit():
            return JsonResponse({'code': 400, 'errmsg': '缺少参数!'})

        if isinstance(count, str) and not count.isdigit():
            return JsonResponse({'code': 400, 'errmsg': '缺少参数!'})

        if selected:
            if not isinstance(selected, bool):
                return JsonResponse({'code': 400, 'errmsg': '缺少参数!'})

        # 3、判断是否登录
        if request.user.is_authenticated:
            # 3.1、已登录写入redis
            redis_conn = get_redis_connection('carts')
            redis_conn.hincrby('carts_%s' % request.user.id, sku_id, count)
            if selected:
                redis_conn.sadd('selected_%s' % request.user.id, sku_id)
            else:
                redis_conn.srem('selected_%s' % request.user.id, sku_id)

            return JsonResponse({'code': 0, 'errmsg': 'ok'})

        else:
            # 3.2、未登录写入cookie
            cart_data = get_carts_from_cookie(request)
            if sku_id in cart_data:
                cart_data[sku_id]['count'] += count
                cart_data[sku_id]['selected'] = selected
            else:
                cart_data[sku_id] = {
                    'count': count,
                    'selected': selected
                }

            data = get_cookie_cart_data(cart_data)

            response = JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('carts', data)
            return response

    def get(self, request):
        cart_dict = {}

        if request.user.is_authenticated:
            # 已登录
            redis_carts, redis_selected = get_redis_carts(request)
            for sku_id, count in redis_carts.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in redis_selected
                }

        else:
            # 未登录
            cart_dict = get_carts_from_cookie(request)

        # 构建购物车商品数据
        sku_ids = cart_dict.keys()
        carts_skus = []

        for sku_id in sku_ids:
            sku = SKU.objects.get(pk=sku_id)
            carts_skus.append({
                'id': sku_id,
                'name': sku.name,
                'selected': cart_dict[sku_id]['selected'],
                'default_image_url': sku.default_image_url,
                'price': sku.price,
                'count': cart_dict[sku_id]['count']
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'cart_skus': carts_skus
        })