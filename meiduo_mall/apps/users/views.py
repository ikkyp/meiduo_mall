import json

from django import http
from django.contrib.auth import login
from django.http import JsonResponse
from django.views import View

from apps.users.models import User


# Create your views here.
class UsernameCountView(View):
    """ 判断用户名是否重复 """
    """ count是该用户名的数量，将会在前端进行验证 """

    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'count': count})


class MobileCountView(View):
    """ 判断手机号是否重复 """
    """ mobile是该号码的数量，将会在前端进行验证 """
    def get(self, request, mobile):
        mobile = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'code': 0, 'errmsg': 'ok', 'mobile': mobile})


class RegisterView(View):
    def post(self, request):
        """ 注册账号 """
        json_dict = json.loads(request.body.decode())  # 前端传输的页面数据
        username = json_dict.get('username')
        password = json_dict.get('password')
        password2 = json_dict.get('password2')
        mobile = json_dict.get('mobile')
        allow = json_dict.get('allow')
        sms_code = json_dict.get('sms_code')
        # 判断参数是否齐全
        if not all([username, password, password2, mobile, allow, sms_code]):
            return http.JsonResponse({'code': 400, 'errmsg': '缺少必传参数!'})
        user = User.objects.create_user(username=username,   # 使用create_user将会对密码直接进行哈希加密处理
                                        password=password,   # 仅django自带的user模型有用
                                        mobile=mobile)
        # 如果注册成功则保持登录状态
        login(request, user)
        return http.JsonResponse({'code': 0, 'errmsg': 'ok'})


# class LoginView(View):
#     """ 用户登录 """
#     def post(self, request):
#         pass
