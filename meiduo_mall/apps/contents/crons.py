from apps.contents.models import ContentCategory
from utils.goods import get_categories


def generic_meiduo_index():
    # 将首页数据进行静态化
    # 商品分类数据
    categories = get_categories()
    # 广告数据
    contents = {}
    content_categories = ContentCategory.objects.all()
    # content_set cat的关联模型content
    for cat in content_categories:
        contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')
    # 需要传送给模板的数据
    content = {
        'contents': contents,
        'categories': categories
    }
    from django.template import loader
    # 加载模板
    index_templates = loader.get_template('index.html')
    # 渲染模板数据
    index_html_data = index_templates.render(content)
    # 将模板数据写入的位置
    import os
    from meiduo_mall import settings
    # os.path.dirname是返回该目录的上层目录
    file_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'front_end_pc/index.html')
    # 将模板数据写入前端中
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(index_html_data)
