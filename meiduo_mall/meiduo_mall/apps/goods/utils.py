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
