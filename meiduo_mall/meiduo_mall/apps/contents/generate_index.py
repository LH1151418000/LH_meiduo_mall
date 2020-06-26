"""
定义一个函数，用于渲染完整的index首页页面，并保存成静态文件；
"""
from django.template import loader
from django.conf import settings
import os
from goods.models import GoodsChannel, GoodsCategory
from contents.models import ContentCategory, Content
from collections import OrderedDict


def generate_index_html():
    """
    生成首页静态页面：
    1、获取动态数据 -- 模版参数
    2、模版渲染 -- 模版参数填充到模板html页面
    :return:
    """

    # ===============频道分组======================
    # categories = {} 无序
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

    # ===============首页广告模版参数==================
    contents = {}
    # 所有广告分类
    content_cats = ContentCategory.objects.all()
    for content_cat in content_cats:
        # content_cat: 广告分类对象 -- 对应页面中的某一个广告位置
        # content['index_lbt'] = [<美图>,<黑色>,<厨卫>,<君乐>] --> 首页轮播图的广告内容
        contents[content_cat.key] = Content.objects.filter(
            category=content_cat,
            status=True
        ).order_by('sequence')

    # ===============模版页面渲染=================
    # loader:函数、传入模版文件，构建一个模版对象
    template = loader.get_template('index.html')

    # 模版参数
    context = {
        'categories': categories,
        'contents': contents
    }

    # context:模版参数，动态数据，用于填充页面
    # 返回值就是一个html页面文本数据
    index_html = template.render(context=context)

    # .../front_end_pc/index.html
    index_path = os.path.join(settings.GENERATED_STATIC_HTML_DIR, 'index.html')
    with open(index_path, 'w') as f:
        f.write(index_html)
