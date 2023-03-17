from decimal import Decimal

from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection
from utils.views import LoginRequiredJSONMixin
from apps.goods.models import SKU
from apps.users.models import Address


class OrderSettlementView(LoginRequiredJSONMixin, View):
    """结算订单"""

    def get(self, request):
        """提供订单结算页面"""
        # 获取登录用户
        user = request.user

        # 查询当前用户的所有地址信息
        addresses = Address.objects.filter(user=request.user,
                                           is_deleted=False)

        # 从Redis购物车中查询出被勾选的商品信息
        redis_conn = get_redis_connection('carts')
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        cart_selected = redis_conn.smembers('selected_%s' % user.id)
        cart = {}
        for sku_id in cart_selected:
            cart[int(sku_id)] = int(redis_cart[sku_id])

        # 查询商品信息
        sku_list = []
        # 查询商品信息
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'count': cart[sku.id],
                'price': sku.price
            })

        # 补充运费
        freight = Decimal('10.00')

        addresses_list = []
        for address in addresses:
            addresses_list.append({
                'id': address.id,
                'province': address.province.name,
                'city': address.city.name,
                'district': address.district.name,
                'place': address.place,
                'receiver': address.receiver,
                'mobile': address.mobile
            })

        # 渲染界面
        context = {
            'addresses': addresses_list,
            'skus': sku_list,
            'freight': freight,
        }

        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'context': context})
