from django.shortcuts import render
from django.views import View

from apps.contents.models import ContentCategory
from utils.goods import get_categories


class IndexView(View):
    """首页广告"""

    def get(self, request):
        """提供首页广告界面"""
        # 查询商品频道和分类(封装在utils里面的goods中)
        categories = get_categories()
        contents = {}
        content_catagories = ContentCategory.objects.all()
        for cat in content_catagories:
            contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')
        # 渲染模板的上下文
        context = {
            'categories': categories,
            'contents': contents
        }
        return render(request, 'index.html', context)
