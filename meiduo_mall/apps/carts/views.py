import base64
import json
import pickle

from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection

from apps.goods.models import SKU


class CartsView(View):
    # 增加购物车
    def post(self, request):
        # 获取数据
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)
        user = request.user
        # 将count转化为int类型
        count = int(count)
        # 判断用户是否登录
        if user.is_authenticated:
            # 链接redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hincrby('carts_%s' % user.id, sku_id, count)
            # 选中状态
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            pl.execute()
            return JsonResponse({'code': 0, 'errmsg': '添加购物车成功'})
        else:
            # 未登录状态
            carts_str = request.COOKIES.get('carts')
            if carts_str:
                cart_dict = pickle.loads(base64.b64decode(carts_str))
            else:
                cart_dict = {}
            if sku_id in cart_dict:
                # 网页中该商品的数量
                addcartcount = cart_dict[sku_id]['count']
                count += addcartcount
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 数据转换加密（将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串）
            cookie_cart = base64.b64encode(pickle.dumps(cart_dict))
            response = JsonResponse({'code': 0, 'errmsg': '添加购物车成功'})
            # decode是将bytes数据转化为字符串，value只能为字符串
            response.set_cookie('carts', cookie_cart.decode(), max_age=7 * 24 * 3600)
            return response

    # 查询购物车
    def get(self, request):
        user = request.user
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            carts = redis_conn.hgetall('carts_%s' % user.id)
            selected = redis_conn.smembers('selected_%s' % user.id)
            cart_dict = {}
            for sku_id, count in carts.items():
                # 数据库中的数据是bytes类型，转化为int类型以便后面操作
                cart_dict[int(sku_id)] = {
                    'count': count,
                    'selected': sku_id in selected,
                }
                # print(sku_id)
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str))
            else:
                cart_dict = {}
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        cart_sku = []
        for sku in skus:
            # print(cart_dict)
            # print(type(cart_dict))
            # print(cart_dict[16])
            cart_sku.append({
                'id': sku.id,
                'price': sku.price,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'selected': cart_dict[sku.id]['selected'],  # 选中状态
                'count': int(cart_dict[sku.id]['count']),  # 数量 强制转换一下
                'amount': sku.price * int(cart_dict[sku.id]['count'])  # 总价格
            })
            # print(type(sku.price))
            # print(type(cart_dict[sku.id]['count']))
        return JsonResponse({'code': 0, 'errmsg': 'OK', 'cart_skus': cart_sku})

    # 修改购物车
    def put(self, request):
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')
        user = request.user
        if user.is_authenticated:
            # 4.登录用户更新redis
            #     4.1 连接redis
            redis_cli = get_redis_connection('carts')
            #     4.2 hash
            redis_cli.hset('carts_%s' % user.id, sku_id, count)
            #     4.3 set
            if selected:
                redis_cli.sadd('selected_%s' % user.id, sku_id)
            else:
                redis_cli.srem('selected_%s' % user.id, sku_id)
            #     4.4 返回响应
            return JsonResponse({'code': 0, 'errmsg': 'ok', 'cart_sku': {'count': count, 'selected': selected}})
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str))
            else:
                cart_dict = {}
            if sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }
            cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict))
            response = JsonResponse({'code': 0, 'errmsg': 'ok', 'cart_sku': {'count': count, 'selected': selected}})
            response.set_cookie('carts', cookie_cart_str.decode(), max_age=14 * 24 * 3600)
            #     5.5 返回响应
            return response

    # 删除购物车
    def delete(self, request):
        user = request.user
        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')

        try:
            SKU.objects.get(pk=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '没有此商品'})

        # 用户登陆状态
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hdel('carts_%s' % user.id, sku_id)
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()
            return JsonResponse({'code': 0, 'errmsg': 'ok'})
        # 用户未登录状态
        else:
            data = request.COOKIES.get('carts')
            if data:
                carts = pickle.loads(base64.b64decode(data))
            else:
                carts = {}

            del carts[sku_id]
            new_carts = base64.b64encode(pickle.dumps(carts))
            response = JsonResponse({'code': 0, 'errmsg': 'ok'})
            response.set_cookie('carts', new_carts.decode(), max_age=14 * 24 * 3600)
            #     5.5 返回响应
            return response


class CartsSelectAllView(View):
    # 全选购物车
    def put(self, request):
        json_dict = json.loads(request.body.decode())
        user = request.user
        selected = json_dict.get('selected')
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            cart = redis_conn.hgetall('carts_%s' % user.id)
            sku_ids = cart.keys()
            for sku_id in sku_ids:
                if selected:
                    redis_conn.sadd('selected_%s' % user.id, sku_id)
                else:
                    redis_conn.srem('selected_%s' % user.id, sku_id)
            return JsonResponse({'code': 0, 'errmsg': '全选购物车成功'})
        else:
            carts_str = request.COOKIES.get('carts')
            response = JsonResponse({'code': 0, 'errmsg': '全选购物车成功'})
            if carts_str:
                cart = pickle.loads(base64.b64decode(carts_str))
                for sku_id in cart:
                    cart[sku_id]['selected'] = selected
                cookie_cart = base64.b64encode(pickle.dumps(cart))
                response.set_cookie('carts', cookie_cart.decode(), max_age=7 * 24 * 3600)
            return response
