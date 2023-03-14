from django import http
from django.contrib.auth.mixins import LoginRequiredMixin


class LoginRequiredJSONMixin(LoginRequiredMixin):

    # 重写LoginRequiredJSONMixin, 当用户不存在时可以返回json数据，而不是匿名函数
    def handle_no_permission(self):
        return http.JsonResponse({'code': 400, 'errmsg': '用户未登录'})
