import base64
import pickle
from django_redis import get_redis_connection


# 合并购物车
def merge_cart_cookie_to_redis(request, user, response):
    cookie_cart_str = request.COOKIES.get('carts')
    if not cookie_cart_str:
        return response
    else:
        cookie_cart_dict = pickle.loads(base64.b64decode(cookie_cart_str))
        new_cart_dict = {}
        new_cart_select_add = []
        new_cart_select_remove = []
        # 同步数据
        for sku_id, cart_dict in cookie_cart_dict.items():
            # 存在redis中的hash表中
            new_cart_dict[sku_id] = cart_dict['count']
            # 判断是否选中
            if cart_dict['selected']:
                new_cart_select_add.append(sku_id)
            else:
                new_cart_select_remove.append(sku_id)
        pl = get_redis_connection('carts').pipeline()
        pl.hmset('carts_%s' % user.id, new_cart_dict)
        if new_cart_select_add:
            pl.sadd('selected_%s' % user.id, *new_cart_select_add)
        if new_cart_select_remove:
            pl.srem('selected_%s' % user.id, *new_cart_select_remove)
        pl.execute()
        # 清除cookie信息
        response.delete_cookie('carts')
        return response
