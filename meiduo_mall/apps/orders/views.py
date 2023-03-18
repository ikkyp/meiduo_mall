import json
import logging
from decimal import Decimal
from time import sleep

from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views import View
from django_redis import get_redis_connection

from apps.goods.models import SKU
from apps.orders.models import OrderInfo, OrderGoods
from apps.users.models import Address
from utils.views import LoginRequiredJSONMixin

logger = logging.getLogger('django')


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


class OrderCommitView(LoginRequiredJSONMixin, View):
    """订单提交"""

    def post(self, request):
        """保存订单信息和订单商品信息"""
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')
        address = Address.objects.get(id=address_id)
        if pay_method not in (OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']):
            return HttpResponseBadRequest('参数pay_method错误')
        user = request.user
        # 订单号
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)
        # 保存订单信息
        # 设置事务
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM[
                        'ALIPAY'] else
                    OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )
                # 获取商品信息和选中状态
                redis_conn = get_redis_connection('carts')
                carts = redis_conn.hgetall('carts_%s' % user.id)
                selected = redis_conn.smembers('selected_%s' % user.id)
                cart_list = {}
                for sku_id in selected:
                    cart_list[int(sku_id)] = int(carts[sku_id])
                cart_keys = cart_list.keys()
                skus = SKU.objects.filter(id__in=cart_keys)
                for sku in skus:
                    while True:
                        # 该商品数量
                        old_stock = sku.stock
                        old_sales = sku.sales
                        sku_count = cart_list[sku.id]
                        if sku_count > old_stock:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'code': 400, 'errmsg': '库存不足'})
                        # 新的库存及销量
                        new_stock = old_stock - sku_count
                        new_sales = old_sales + sku_count
                        # 构建乐观锁
                        result = SKU.objects.filter(id=sku.id, stock=old_stock).update(stock=new_stock, sales=new_sales)
                        # 代表更新失败，进行写一次循环
                        if result == 0:
                            sleep(0.05)  # 进行睡眠，减轻数据库负担
                            continue
                        # 保存订单商品信息 OrderGoods（多）
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price,
                        )
                        # 保存商品订单中总价和总数量
                        order.total_count += sku_count
                        order.total_amount += (sku_count * sku.price)
                        break
                order.total_amount += order.freight
                order.save()
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                return JsonResponse({'code': 400, 'errmsg': '下单失败'})
        # 提交事务
        transaction.savepoint_commit(save_id)
        # 清除购物车中已结算的商品
        pl = redis_conn.pipeline()
        pl.hdel('carts_%s' % user.id, *selected)
        pl.srem('selected_%s' % user.id, *selected)
        pl.execute()

        # 响应提交订单结果
        return JsonResponse({'code': 0, 'errmsg': '下单成功', 'order_id': order.order_id})
