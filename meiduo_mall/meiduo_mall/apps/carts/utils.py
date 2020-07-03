import base64, pickle
from django_redis import get_redis_connection


def get_carts_from_cookie(request):
    """
    获取cookie中的购物车数据
    :param request: 请求对象
    :return: 购物车字典
    """
    carts_from_cookie = request.COOKIES.get('carts')
    if carts_from_cookie:
        carts_dict = base64.b64decode(carts_from_cookie.encode())
        carts_dict = pickle.loads(carts_dict)
        return carts_dict
    else:
        return {}


def get_cookie_cart_data(cookie_cart):
    """
    使用pickle和base64对购物车字典数据，编码得出存储到cookie中的字符串
    :param cookie_cart: 购物车字典
    :return: 经过pickle和base64编码后的字符串
    """
    # "BNHJBLOhBHYUKNLNJIK="
    return base64.b64encode(
        pickle.dumps(cookie_cart)
    ).decode()


def get_redis_carts(request):
    user_id = request.user.id
    redis_cart = None
    redis_selected = None

    redis_conn = get_redis_connection('carts')
    redis_cart = redis_conn.hgetall('carts_%s' % user_id)
    redis_selected = redis_conn.smembers('selected_%s' % user_id)

    # 判断是否存在
    if not redis_cart:
        redis_cart = {}
    if not redis_selected:
        redis_selected = set()

    return redis_cart, redis_selected


def merge_cart_cookie_to_redis(request, user, response):
    cookie_cart = get_carts_from_cookie(request)
    if not cookie_cart:
        return response
    redis_cart = get_redis_connection('carts')
    for sku_id, item in cookie_cart.items():
        redis_cart.hset('carts_%s' % user.id, sku_id, item['count'])
        if item['selected']:
            redis_cart.sadd('selected_%s' % user.id, sku_id)
        else:
            redis_cart.srem('selected_%s' % user.id, sku_id)
    response.delete_cookie('carts')
    return response

