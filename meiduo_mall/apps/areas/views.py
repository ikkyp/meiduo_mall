import json

from django.core.cache import cache
from django.http import JsonResponse
from django.views import View

from apps.areas.models import Area
from apps.users.models import Address
from utils.views import LoginRequiredJSONMixin


class AreasView(View):
    def get(self, request):
        # 查看是否有缓存
        if not cache.get('province_list'):
            # 查询省级数据（省级数据的parent为空）(返回的是对象)
            province_list_model = Area.objects.filter(parent__isnull=True)
            # 序列化数据
            province_list = []
            for province in province_list_model:
                province_list.append({
                    'id': province.id,
                    'name': province.name,
                })
            # 将数据进行缓存，减少数据的查询
            cache.set('province_list', province_list, 3600)
            return JsonResponse({
                'code': 200,
                'errmsg': 'ok',
                'province_list': province_list
            })
        else:
            province_list = cache.get('province_list')
            return JsonResponse({
                'code': 200,
                'errmsg': 'ok',
                'province_list': province_list
            })


class SubAreasView(View):
    def get(self, request, pk):
        # 查询市的父级
        parent_model = Area.objects.get(id=pk)
        # 市的对象的集合
        sub_model = parent_model.subs.all()
        sub_list = []
        for subs in sub_model:
            sub_list.append({
                'id': subs.id,
                'name': subs.name
            })
        # 父级的数据传入到后端（含有子级的信息）
        parent_list = {
            'id': parent_model.id,
            'name': parent_model.name,
            'subs': sub_list
        }
        return JsonResponse({
            'code': 200,
            'errmsg': 'ok',
            'sub_data': parent_list
        })


class CreateAddressView(LoginRequiredJSONMixin, View):
    # 新增用户收货地址
    def post(self, request):
        count = request.user.addresses.count()
        # 地址最多为20，超过了则报错
        if count >= 20:
            return JsonResponse({'code': 400, 'errmsg': '超过地址数量上限'})
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 创建地址
        address = Address.objects.create(
            user=request.user,
            title=receiver,
            receiver=receiver,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            place=place,
            mobile=mobile,
            tel=tel,
            email=email
        )
        # 如果用户没有默认地址则改为默认地址
        if not request.user.default_address:
            request.user.default_address = address
            request.user.save()
        # 将新创建的地址转化为json数据返回给前端
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }
        return JsonResponse({'code': 0, 'errmsg': '新增地址成功', 'address': address_dict})


class AddressView(View):
    """展示用户收货地址"""

    def get(self, request):
        user = request.user
        addresses = Address.objects.filter(user=user, is_deleted=False)

        address_dict_list = []
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            if address.id == user.default_address:
                address_dict_list.insert(0, address_dict)
            else:
                address_dict_list.append(address_dict)
        default_id = user.default_address_id
        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'addresses': address_dict_list,
                             'default_address_id': default_id})


class UpdateDestroyAddressView(LoginRequiredJSONMixin, View):
    def put(self, request, address_id):
        """修改地址"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 判断地址是否存在,并更新地址信息
        Address.objects.filter(id=address_id).update(
            user=request.user,
            title=receiver,
            receiver=receiver,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            place=place,
            mobile=mobile,
            tel=tel,
            email=email
        )

        # 构造响应数据
        address = Address.objects.get(id=address_id)
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 响应更新地址结果
        return JsonResponse({'code': 0, 'errmsg': '更新地址成功', 'address': address_dict})

    def delete(self, request, address_id):
        # 删除地址
        address = Address.objects.get(id=address_id)
        # is_deleted在模型中设值，为True是则逻辑删除，无法查询到该数据，
        # 当其的值为False时则可以查询到该数据
        address.is_deleted = True
        address.save()
        return JsonResponse({'code': 0, 'errmsg': '删除地址成功'})


class DefaultAddressView(LoginRequiredJSONMixin, View):
    # 设置默认地址
    def put(self, request, address_id):
        address = Address.objects.get(id=address_id)
        request.user.default_address = address
        request.user.save()
        return JsonResponse({'code': 0, 'errmsg': '设置默认地址成功'})


class UpdateTitleAddressView(LoginRequiredJSONMixin, View):
    """设置地址标题"""

    def put(self, request, address_id):
        address = Address.objects.get(id=address_id)
        title = json.loads(request.body.decode()).get('title')
        address.title = title
        address.save()
        return JsonResponse({'code': 0, 'errmsg': '设置地址标题成功'})
