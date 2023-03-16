#!/usr/bin/env python
# 指定该脚本是python
import os
import sys

import django
from django.template import loader

from meiduo_mall import settings
from utils.goods import get_breadcrumb, get_categories, get_goods_specs
from apps.goods.models import SKU
"""
详情页面 与 首页不同
详情页面的内容变化比较少。一般也就是修改商品的价格

1. 详情页面 应该在上线的时候 统一都生成一遍
2. 应该是运营人员修改的时候生成 （定时任务）

"""
# ../ 当前目录的上一级目录，也就是 base_dir
sys.path.insert(0, '../')
# 告诉 os 我们的django的配置文件在哪里
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings")
# django setup
# 相当于 当前的文件 有了django的环境
django.setup()


def generic_detail_html(sku):
    categories = get_categories()
    breadcrumb = get_breadcrumb(sku.category)
    specs = get_goods_specs(sku)
    content = {
        'categories': categories,
        'breadcrumb': breadcrumb,
        'specs': specs,
        'sku': sku
    }
    detail_html = loader.get_template('detail.html')
    detail_html_data = detail_html.render(content)
    file_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'front_end_pc/goods/%s.html' % sku.id)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(detail_html_data)


# 把每个商品页面都重新静态化一遍
skus = SKU.objects.all()
for s in skus:
    generic_detail_html(s)
