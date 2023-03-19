import json
import logging
import re

from django import http
from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection

from apps.users.models import User
from meiduo_mall import settings
from utils.views import LoginRequiredJSONMixin

logger = logging.getLogger('django')


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

        # 验证短信验证码
        redis_conn = get_redis_connection('code')
        sms_code_server = redis_conn.get(mobile)
        # 判断短信验证码是否过期
        if not sms_code_server:
            return http.JsonResponse({'code': 400, 'errmsg': '短信验证码失效'})
        # 对比用户输入的和服务端存储的短信验证码是否一致
        if sms_code != sms_code_server.decode():  # sms_code_server是byte,需要解码对比
            return http.JsonResponse({'code': 400, 'errmsg': '短信验证码有误'})

        user = User.objects.create_user(username=username,  # 使用create_user将会对密码直接进行哈希加密处理
                                        password=password,  # 仅django自带的user模型有用
                                        mobile=mobile)
        # 如果注册成功则保持登录状态
        login(request, user)
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)
        return response


class LoginView(View):
    """ 用户登录 """

    def post(self, request):
        # 浏览器提交的数据
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        remembered = data.get('remembered')

        if not all([username, password]):
            return JsonResponse({'code': 400, 'errmsg': '缺少参数'})

        # 判断用户使用的是手机号登录还是用户名登录
        if re.match('1[3-9]\d{9}', username):
            User.USERNAME_FIELD = 'mobile'
        else:
            User.USERNAME_FIELD = 'username'

        # 验证该账户密码是否能够登录
        user = authenticate(username=username, password=password)
        if user is None:
            return JsonResponse({'code': 400, 'errmsg': '用户名或密码错误'})

        # 账号密码正确则直接登录,状态保持
        login(request, user)

        # 判断是否记住用户
        if remembered:
            request.session.set_expiry(None)  # 两周内无需再次登录
        else:
            request.session.set_expiry(0)  # 浏览器关闭即退出登录
        # 用户名展示
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.set_cookie('username', username, max_age=3600 * 24 * 15)
        # 合并购物车
        from apps.carts.utils import merge_cart_cookie_to_redis
        response = merge_cart_cookie_to_redis(request, user, response)
        return response


class LogoutView(View):
    """ 用户退出 """

    def delete(self, request):
        logout(request)
        response = JsonResponse({'code': 0, 'errmsg': 'ok'})
        response.delete_cookie('username')
        return response


class CenterView(LoginRequiredJSONMixin, View):
    def get(self, request):
        # 当用户处于登录状态时，返回用户的基本信息， 否则通过LoginRequiredJSONMixin返回错误信息
        info_data = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return JsonResponse({'code': 200, 'info_data': info_data, 'errmsg': 'ok'})


class EmailView(LoginRequiredJSONMixin, View):
    def put(self, request):
        # 修改用户邮箱
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')
        # 校验参数
        if not email:
            return http.JsonResponse({'code': 400,
                                      'errmsg': '缺少email参数'})
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400, 'errmsg': '添加邮箱失败'})
        # 发送邮箱进行验证
        from celery_tasks.email.tasks import send_verify_email
        user = request.user
        verify_url = settings.EMAIL_VERIFY_URL + '?user_id=%s&&email=%s' % (user.id, user.email)
        send_verify_email(email, verify_url)
        return JsonResponse({'code': 200, 'errmsg': '添加邮箱成功'})


class VerifyEmailView(View):
    # 验证数据库是否含有该用户，并将该用户邮箱改为激活
    def put(self, request):
        user_id = request.GET.get('user_id')
        email = request.GET.get('email')
        try:
            user = User.objects.get(id=user_id, email=email)
        except User.DoesNotExist as e:
            logger.error(e)
            return JsonResponse({'code': 400, 'errmsg': '参数有误!'})
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 0, 'errmsg': '激活失败!'})
        return JsonResponse({'code': 0, 'errmsg': 'ok'})


class ChangePasswordView(View):
    # 修改密码
    def put(self, request):
        user = request.user
        json_dict = json.loads(request.body.decode())
        old_password = json_dict.get('old_password')
        new_password = json_dict.get('new_password')
        new_password2 = json_dict.get('new_password2')

        # 校验参数
        if not all([old_password, new_password, new_password2]):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})
        if not user.check_password(old_password):
            return JsonResponse({'code': 400,
                                 'errmsg': '原始密码不正确'})
        if new_password != new_password2:
            return JsonResponse({'code': 400,
                                 'errmsg': '两次输入密码不一致'})
        user.set_password(new_password)
        user.save()
        # 退出登录
        logout(request)
        response = JsonResponse({'code': 0,
                                 'errmsg': 'ok'})
        response.delete_cookie('username')
        return response
