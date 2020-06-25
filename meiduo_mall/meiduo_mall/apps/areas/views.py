from django.shortcuts import render
from django import http
from areas.models import Area
from django.views import View
from django.core.cache import cache

# Create your views here.


class ProvinceAreasView(View):

    def get(self, request):
        # province = Area.objects.filter(parent__isnull=True)
        province = Area.objects.filter(parent=None)

        province_list = cache.get('province_list')

        if not province_list:
            province_list = []
            for i in province:
                province_list.append(
                    {'id': i.id,
                     'name': i.name}
                )
            cache.set('province_list', province_list, 3600)

        return http.JsonResponse({'code': 0, 'errmsg': 'ok', 'province_list': province_list})


# from django.core.cache import cache
# 存储缓存数据：cache.set('key', 内容, 有效期)
# 读取缓存数据：cache.get('key')
# 删除缓存数据：cache.delete('key')


class SubAreasView(View):

    def get(self, request, pk):
        # 市
        sub_province = Area.objects.filter(parent=pk)
        # 省
        province = Area.objects.get(id=pk)

        sub_data = cache.get('sub_area_' + pk)

        if not sub_data:
            # 市
            sub_list = []
            for i in sub_province:
                sub_list.append(
                    {'id': i.id,
                     'name': i.name}
                )
            sub_data = {
                'id': province.id,
                'name': province.name,
                'subs': sub_list
            }
            cache.set('sub_area_' + pk, sub_data, 3600)
        return http.JsonResponse({'code': 0, 'errmsg': 'ok', 'sub_data': sub_data})
