from random import randint

from django.http import HttpResponse, JsonResponse
from django.views import View
from django_redis import get_redis_connection

from celery_tasks.sms.tasks import celery_send_sms_code
from libs.captcha.captcha import captcha


class ImageCodeView(View):
    """ 生成图片验证码并保存 """

    def get(self, request, uuid):
        # 获取图片验证码的文本信息以及图片
        text, image = captcha.generate_captcha()
        # 链接redis数据库
        redis_cli = get_redis_connection('code')
        # 将文本信息保存在redis中方便后面进行验证, uuid是图形验证码的编号
        redis_cli.setex(uuid, 100, text)
        # 由于图片是二进制格式，所以用HttpResponse
        # content_type 是告诉响应数据，这是什么格式的图片
        return HttpResponse(image, content_type='image/jpeg')


class SmsCodeView(View):
    def get(self, request, mobile):
        """ 验证图形验证码的信息并发送短信 """
        # 获取请求参数
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')
        if not all([image_code, uuid]):
            return JsonResponse({'code': 400, 'errmsg': '参数不全'})

        # 链接redis code库
        redis_cli = get_redis_connection('code')
        # 获取图形验证码的文本值
        redis_imag_code = redis_cli.get(uuid)
        # 对比验证码信息
        if redis_imag_code is None:
            return JsonResponse({'code': 400, 'errmsg': '图片验证码已过期'})
        if redis_imag_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': 400, 'errmsg': '图片验证码错误'})

        # 获取标记,防止用户多次发送短信，浪费资源
        send_flag = redis_cli.get('send_flag_%s' % mobile)
        if send_flag is not None:
            return JsonResponse({'code': 400, 'errmsg': '不要频繁发送短信'})
        # 随机短信验证码
        sms_code = "%06d" % randint(0, 99999)

        # 新建管道
        pipeline = redis_cli.pipeline()
        # 保存短信验证码
        pipeline.setex(mobile, 300, sms_code)
        # 设置标记，避免多次重复发送验证码（标记有效期一分钟）
        pipeline.setex('send_flag_%s' % mobile, 60, 1)
        # 执行管道内的指令，减少redis数据库的访问次数
        pipeline.execute()
        # 执行celery中的短信发送模块(测试阶段，不发送信息)
        celery_send_sms_code.delay(mobile, sms_code)
        return JsonResponse({'code': 0, 'errmsg': 'ok'})
