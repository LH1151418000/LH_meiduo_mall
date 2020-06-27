from haystack import indexes
from .models import SKU


# 1、模型类名字：<Django模型类>Index
# 2、继承：indexes.SearchIndex, indexes.Indexable
# 3、定义类属性text(固定的名字) —— 在es中检索的字段
class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    """SKU索引数据模型类"""
    # document=True:表名该字段是主要进行关键字查询的字段
    # document=True，定义当前text是用于检索的es索引表中的字段
    # use_template:表示后续通过模板来指明
    # use_template=True, 通过定义模版方式，指定存入es索引表中的django模型类字段
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        """返回建立索引的模型类"""
        return SKU

    def index_queryset(self, using=None):
        """返回要建立查询的数据查询集"""
        return self.get_model().objects.filter(is_launched=True)