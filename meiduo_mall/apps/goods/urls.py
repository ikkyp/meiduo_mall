from django.urls import path

from apps.goods.views import ListView, HotGoodsView, MySearchView, DetailView, CategoryVisitCountView

urlpatterns = [
    path('list/<category_id>/skus/', ListView.as_view()),
    path('hot/<category_id>/', HotGoodsView.as_view()),
    path('search/', MySearchView()),  # 由于使用的方法不是get或者post方法，所以不能使用as_view()
    path('detail/<sku_id>/', DetailView.as_view()),
    path('detail/visit/<category_id>/', CategoryVisitCountView.as_view()),
]
