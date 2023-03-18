from django.urls import path, include
from utils.converters import UsernameConverter, MobileConverter, UUIDConverter
from django.urls import register_converter

# 注册转换器
register_converter(UsernameConverter, 'username')
register_converter(MobileConverter, 'mobile')
register_converter(UUIDConverter, 'uuid')

urlpatterns = [
    path('', include('apps.users.urls')),
    path('', include('apps.verifications.urls')),
    path('', include('apps.oauth.urls')),
    path('', include('apps.areas.urls')),
    path('', include('apps.contents.urls')),
    path('', include('apps.goods.urls')),
    path('', include('apps.carts.urls')),
    path('', include('apps.orders.urls')),
    path('', include('apps.pay.urls')),
]
