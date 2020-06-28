from django.shortcuts import render
from django.views import View
from goods.models import GoodsCategory, SKU
from .utils import get_breadcrumb
from django.core.paginator import Paginator, EmptyPage
from django.http import JsonResponse


# Create your views here.


class ListView(View):
    """商品列表页"""

    def get(self, request, category_id):
        page_num = request.GET.get('page')  # 当前页码
        page_size = request.GET.get('page_size')  # 获取每页数量
        sort = request.GET.get('ordering')  # 获取排序方式

        # 获取三级菜单分类信息
        category = GoodsCategory.objects.get(id=category_id)

        # 面包屑导航
        breadcrumb = get_breadcrumb(category)

        # 排序方式
        skus = SKU.objects.filter(category=category, is_launched=True).order_by(sort)

        # 获取每页商品数据
        paginator = Paginator(skus, page_size)

        page_skus = paginator.page(page_num)

        # 获取列表页总页数
        total_page = paginator.num_pages

        # 定义列表
        list = []
        # 整理格式：
        for sku in page_skus:
            list.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

            # 把数据变为json发送给前端
        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'breadcrumb': breadcrumb,
            'list': list,
            'count': total_page
        })


class HotGoodsView(View):
    """热销排行"""

    def get(self, request, category_id):
        """提供商品热销排行 JSON 数据"""
        # 根据效率倒序
        skus = SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[:2]

        # 转换格式
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

        return JsonResponse({'code': 0, 'errmsg': 'ok', 'hot_skus': hot_skus})


from haystack.views import SearchView


class MySearchView(SearchView):

    def create_response(self):
        """
        重写，自定义返回JsonResponse
        :return:
        """
        # 获取搜索结果
        data = self.get_context()
        # data['query']: 用户搜索词
        # data['page']: django分页对象——当前页
        # data['page'].object_list分页结果,是SearchResult对象；SearchResult.object属性是对应SKU对象
        # data['paginator']: django分页器对象

        # es搜索的结果——sku对象转化而成的字典！
        data_list = []
        for result in data['page'].object_list:
            # result: 是SearchResult对象
            # result.object：是sku对象
            data_list.append({
                'id': result.object.id,
                'name': result.object.name,
                'price': result.object.price,
                'default_image_url': result.object.default_image_url,
                'searchkey': data['query'],
                'page_size': data['paginator'].per_page,  # 每页数量
                'count': data['paginator'].num_pages  # 搜索的结果总数
            })

        # 默认JsonResponse只能传入字典，如果传入列表必须设置safe=False
        return JsonResponse(data_list, safe=False)


