# ===========================================================================
# import os, sys
# # 需要把外层meiduo_mall加入导包路径
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings.dev')
# # sys.path.insert(0, '/Users/lh/Desktop/LH_meiduo_mall/meiduo_mall')
# # 加载Django环境
# import django
# django.setup()
# ===========================================================================

from collections import OrderedDict
from goods.models import GoodsChannel, GoodsCategory, SKU, GoodsSpecification, SpecificationOption
from django.template import loader
from django.conf import settings
from goods.models import SKUSpecification
from copy import deepcopy
import os

def get_breadcrumb(category):
    """
    封装面包屑导航
    :param category: 商品类别
    :return: 面包屑导航字典
    """

    # 定义一个字典：
    breadcrumb = {
        'cat1': '',
        'cat2': '',
        'cat3': '',
    }

    # 判断传入的category是那个时候级别
    # 这里的category是GoodsCategory对象
    if category.parent is None:
        # 当前类别为 1 级
        breadcrumb['cat1'] = category.name
    elif category.parent.parent is None:
        # 当前为 2 级
        breadcrumb['cat2'] = category.name
        breadcrumb['cat1'] = category.parent.name
    else:
        # 当前为 3 级
        breadcrumb['cat3'] = category.name
        breadcrumb['cat2'] = category.parent.name
        breadcrumb['cat1'] = category.parent.parent.name

    return breadcrumb


def get_categories():
    categories = OrderedDict()  # 有序字典

    channels = GoodsChannel.objects.order_by(
        # order_by传入多个字段排序，如果group_id一样，按照sequence
        'group_id',
        'sequence'
    )

    for channel in channels:
        # channel：每个频道对象
        # 模版参数中，第一次遍历到该分组，那么就这categories添加一个
        if channel.group_id not in categories:
            categories[channel.group_id] = {
                'channels': [],  # 当前频道组的1级分类
                'sub_cats': []  # 2级分类
            }
        # 构建当前分组的频道和分类信息
        cat1 = channel.category
        categories[channel.group_id]['channels'].append({
            'id': cat1.id,
            'name': cat1.name,
            'url': channel.url
        })

        # 所有父级分类是cat1这个1级分类的2级分类
        cat2s = GoodsCategory.objects.filter(
            parent=cat1,
        )
        for cat2 in cat2s:
            # 每一个2级分类的对象
            cat3_list = []  # 根据cat2这个2级分类获取3级分类
            cat3s = GoodsCategory.objects.filter(
                parent=cat2
            )
            for cat3 in cat3s:
                # cat3:每一个3级分类对象
                cat3_list.append({
                    'id': cat3.id,
                    'name': cat3.name
                })

            categories[channel.group_id]['sub_cats'].append({
                'id': cat2.id,
                'name': cat2.name,
                'sub_cats': cat3_list  # 3级分类
            })
    return categories


def get_goods_and_spec(sku_id):
    # 当前sku商品
    sku = SKU.objects.get(pk=sku_id)
    # 记录当前sku选项组合
    cur_sku_spec_options = SKUSpecification.objects.filter(sku=sku).order_by('spec_id')
    cur_sku_options = []
    for temp in cur_sku_spec_options:
        # temp是SKUSpecification中间表对象
        cur_sku_options.append(temp.option_id)

    # Goods对象（SPU商品）
    goods = sku.goods
    # 罗列出和当前sku同类的所有商品选项和商品id的映射关系
    # {(1,4,7):1, (1,3,7):2}
    sku_options_mapping = {}
    skus = SKU.objects.filter(goods=goods)
    for temp_sku in skus:
        # temp_sku:每一个sku商品对象
        sku_spec_options = SKUSpecification.objects.filter(sku=temp_sku).order_by('spec_id')
        sku_options = []
        for temp in sku_spec_options:
            sku_options.append(temp.option_id)  # [1,4,7]

        sku_options_mapping[tuple(sku_options)] = temp_sku.id  # {(1,4,7):1}

    # specs
    specs = GoodsSpecification.objects.filter(goods=goods).order_by('id')
    # 在每个规格对象中动态追加一个属性spec_options来记录当前规格有哪些选项
    for index, spec in enumerate(specs):
        # spec每一个规格对象
        options = SpecificationOption.objects.filter(spec=spec)

        # 每一次选项规格的时候，准备一个当前sku的选项组合列表，便于后续使用
        temp_list = deepcopy(cur_sku_options)
        for option in options:
            # 每一个选项,动态添加一个sku_id值，来确定这个选项是否属于当前sku商品
            temp_list[index] = option.id
            option.sku_id = sku_options_mapping.get(tuple(temp_list))

        # 在每个规格对象中动态追加一个属性spec_options来记录当前规格有哪些选项
        spec.spec_options = options

    return goods, sku, specs

# ======定义一个函数，实现渲染sku商品详情页面

def generate_static_sku_detail_html(sku_id):
    # 分组频道参数
    categories = get_categories()

    goods, sku, specs = get_goods_and_spec(sku_id)

    # ==================模版渲染===================
    # 构建模版参数
    context = {
        'categories': categories,  # 构建详情页商品频道
        'goods': goods,  # 当前sku商品的spu商品（goods模型类）
        'sku': sku,
        'specs': specs  # 传入的是当前sku商品从属的spu拥有的规格及其选项
    }

    # 获取模版
    template = loader.get_template('detail.html')

    # 调用模版渲染函数，得出完整html页面
    sku_html_text = template.render(context=context)
    # 写入静态文件
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_DIR,
                             'goods/' + str(sku_id) + '.html')

    with open(file_path, 'w') as f:
        f.write(sku_html_text)


# if __name__ == '__main__':
#     for num in range(1,17):
#         generate_static_sku_detail_html(num)
