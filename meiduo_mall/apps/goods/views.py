import json
from datetime import date

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from haystack.views import SearchView

from apps.goods.models import SKU, GoodsCategory, GoodsVisitCount
from utils.goods import get_breadcrumb, get_categories, get_goods_specs


class ListView(View):
    """商品列表页"""

    def get(self, request, category_id):
        # 1.接收参数
        # 排序字段
        ordering = request.GET.get('ordering')
        # 每页多少条数据
        page_size = request.GET.get('page_size')
        # 要第几页数据
        page = request.GET.get('page')
        # 2.获取分类id
        # 3.根据分类id进行分类数据的查询验证
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '参数缺失'})
        # 4.获取面包屑数据
        breadcrumb = get_breadcrumb(category)
        # 5.查询分类对应的sku数据，然后排序，然后分页
        skus = SKU.objects.filter(category=category, is_launched=True).order_by(ordering)
        # 分页
        # object_list, per_page
        # object_list   列表数据
        # per_page      每页多少条数据
        paginator = Paginator(skus, per_page=page_size)

        # 获取指定页码的数据
        page_skus = paginator.page(page)

        sku_list = []
        # 将对象转换为字典数据
        for sku in page_skus.object_list:
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })

        # 获取总页码
        total_num = paginator.num_pages

        # 6.返回响应
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'list': sku_list, 'count': total_num, 'breadcrumb': breadcrumb})


class HotGoodsView(View):
    """商品热销排行"""

    def get(self, request, category_id):
        """提供商品热销排行JSON数据"""
        # 根据销量倒序
        skus = SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[:2]

        # 序列化
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image.url,
                'name': sku.name,
                'price': sku.price
            })

        return JsonResponse({'code': 0, 'errmsg': 'OK', 'hot_skus': hot_skus})


class MySearchView(SearchView):
    # 重写SearchView类
    def create_response(self):
        # 获取搜索结果
        context = self.get_context()
        data_list = []
        for sku in context['page'].object_list:
            data_list.append({
                'id': sku.object.id,
                'name': sku.object.name,
                'price': sku.object.price,
                'default_image_url': sku.object.default_image.url,
                'searchkey': context.get('query'),
                'page_size': context['page'].paginator.num_pages,
                'count': context['page'].paginator.count
            })
        # 拼接参数, 返回
        return JsonResponse(data_list, safe=False)


class DetailView(View):
    """商品详情页"""

    def get(self, request, sku_id):
        """提供商品详情页"""
        # 获取当前sku的信息
        sku = SKU.objects.get(id=sku_id)
        # 查询商品频道分类
        categories = get_categories()
        # 查询面包屑导航
        breadcrumb = get_breadcrumb(sku.category)
        # 查询商品规格信息
        goods_specs = get_goods_specs(sku_id)
        # 渲染页面
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'specs': goods_specs,
        }
        return render(request, 'detail.html', context)


class CategoryVisitCountView(View):
    # 商品数据访问量
    def post(self, request, category_id):
        # 1.接收分类id
        # 2.验证参数（验证分类id）
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return JsonResponse({'code': 400, 'errmsg': '没有此分类'})
        # 3.查询当天 这个分类的记录有没有

        today = date.today()
        try:
            gvc = GoodsVisitCount.objects.get(category=category, date=today)
        except GoodsVisitCount.DoesNotExist:
            # 4. 没有新建数据
            GoodsVisitCount.objects.create(category=category,
                                           date=today,
                                           count=1)
        else:
            # 5. 有的话更新数据
            gvc.count += 1
            gvc.save()
        # 6. 返回响应
        return JsonResponse({'code': 0, 'errmsg': 'ok'})


class UserBrowseHistory(View):
    # 用户浏览记录
    def post(self, request):
        # 获取商品id
        sku_id = json.loads(request.body.decode()).get('sku_id')
        # 登录用户id
        user_id = request.user.id
        # 链接数据库并保存商品id
        redis_conn = get_redis_connection('history')
        p1 = redis_conn.pipeline()
        # 去除重复的浏览记录(0表示移除所有的与value相同的值)
        '''
            count > 0 : 从表头开始向表尾搜索，移除与 VALUE 相等的元素，数量为 COUNT 。
            count < 0 : 从表尾开始向表头搜索，移除与 VALUE 相等的元素，数量为 COUNT 的绝对值。
            count = 0 : 移除表中所有与 VALUE 相等的值。
        '''
        p1.lrem('history_%s' % user_id, 0, sku_id)
        # 存数据
        p1.lpush('history_%s' % user_id, sku_id)
        # 截取数据（最多保存五条浏览记录）
        p1.ltrim('history_%s' % user_id, 0, 4)
        p1.execute()
        return JsonResponse({'code': 0, 'errmsg': 'OK'})

    # 获取用户浏览记录
    def get(self, request):
        # 获取id
        user = request.user
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % user.id, 0, -1)
        # 获取商品信息并传入前端
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })
        return JsonResponse({'code': 0, 'errmsg': 'OK', 'skus': skus})
