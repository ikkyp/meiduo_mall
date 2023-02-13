from django.urls import path, include
from utils.converters import UsernameConverter, MobileConverter
from django.urls import register_converter

# 注册转换器
register_converter(UsernameConverter, 'username')
register_converter(MobileConverter, 'mobile')

urlpatterns = [
    path('', include('apps.users.urls')),
    path('', include('apps.verifications.urls')),


]
