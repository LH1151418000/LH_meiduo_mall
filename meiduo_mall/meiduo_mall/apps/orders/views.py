import json
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from users.models import Address
from carts.utils import *
from goods.models import SKU
from django.http import JsonResponse
from decimal import Decimal
from django.utils import timezone
from .models import *
from django.db import transaction  # 事务


# Create your views here.

# 结算页面
class OrderSettlementView(LoginRequiredMixin, View):

    def get(self, request):
        # 用户进入结算页面，将用户数据返回
        user = request.user

        # 用户可选地址
        addresses_queryset = Address.objects.filter(user=user, is_deleted=False)

        addresses = []
        for address in addresses_queryset:
            addresses.append({
                'id': address.id,
                'province': address.province.name,
                'city': address.city.name,
                'district': address.district.name,
                'place': address.mobile,
                'receiver': address.receiver
            })

        # 用户购物车数据
        # redis_cart = {b'商品id', b'商品个数'}
        # redis_selected = {b'商品id'}
        redis_cart, redis_selected = get_redis_carts(request)

        skus = []
        for sku_id in redis_selected:
            sku = SKU.objects.get(pk=int(sku_id))
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image_url,
                'count': int(redis_cart[sku_id]),
                'price': sku.price
            })

        # 构建响应数据
        freight = Decimal('10.0')
        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'context': {
                'addresses': addresses,
                'skus': skus,
                'freight': freight
            }
        })


# 保存订单和提交订单
class OrderCommitView(LoginRequiredMixin, View):

    def post(self, request):
        # ================新建订单数据================
        # 获取订单数据
        json_dict = json.loads(request.body)
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')

        # 校验获取到到数据
        if not all([address_id, pay_method]):
            return JsonResponse({'code': 400, 'errmsg': '获取数据失败'})
        if pay_method not in [1, 2]:
            return JsonResponse({'code': 400, 'errmsg': '传入参数错误'})
        if not isinstance(address_id, int):
            return JsonResponse({'code': 400, 'errmsg': '传入参数错误'})

        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + '%06d' % request.user.id

        # 创建事务
        with transaction.atomic():
            # 创建事务保存点
            save_id = transaction.savepoint()
            order = OrderInfo(
                order_id=order_id,
                user=request.user,
                address_id=address_id,
                total_count=0,
                total_amount=Decimal('0'),
                freight=Decimal('10.0'),
                pay_method=pay_method,
                ###
            )
            # 新建从表前要先建主表
            order.save()
            # ============新建订单商品=============

            redis_cart, redis_selected = get_redis_carts(request)
            # skus = SKU.objects.filter(id__in=redis_selected)

            cart_dict = {}
            for sku_id, count in redis_cart.items():
                if sku_id in redis_selected:
                    cart_dict[int(sku_id)] = {
                        'count': int(count),
                        'selected': sku_id in redis_selected
                    }

            sku_ids = cart_dict.keys()
            for sku_id in sku_ids:
                while True:
                    # sku_id = str(sku.id).encode()
                    # count = int(redis_cart[sku_id])

                    # 乐观锁第一次读取
                    sku = SKU.objects.get(pk=sku_id)

                    old_stock = sku.stock
                    old_sales = sku.sales

                    count = cart_dict[sku_id]['count']

                    if count > old_stock:
                        # 返回事务保存点
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'code': 400, 'errmsg': '超出库存'})

                    # 销量累加，库存减少
                    # sku.sales += count
                    # sku.stock -= count
                    new_stock = old_stock - count
                    new_sales = old_sales + count

                    result = SKU.objects.filter(pk=sku.id, stock=old_stock, sales=old_sales).update(stock=new_stock, sales=new_sales)
                    if result == 0:
                        continue

                    order_goods = OrderGoods(
                        order=order,
                        sku=sku,
                        count=int(count),
                        price=sku.price,
                    )
                    order_goods.save()
                    break
                # 同类商品销量累加
                spu = sku.goods
                spu.sales += count

                # 保存商品订单中总价和总数量
                order.total_count += count
                order.total_amount += (count * sku.price)

            # 添加邮费和保存订单信息
            order.total_amount += order.freight
            order.save()

            # 清除购物车中已结算的商品
            user = request.user
            redis_conn = get_redis_connection('carts')
            redis_conn.hdel('carts_%s' % user.id, *redis_selected)
            redis_conn.srem('selected_%s' % user.id, *redis_selected)

        # 响应提交订单结果
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'order_id': order_id})
