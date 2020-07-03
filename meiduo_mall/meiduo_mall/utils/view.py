from django.http import JsonResponse


# 视图函数装饰器，来完成登陆验证
def login_required(view):
    def wrapper(request, *args, **kwargs):
        # 添加登陆验证
        if not request.user.is_authenticated:
            # 未登陆
            return JsonResponse({
                'code': 400,
                'errmsg': '未登陆！'
            })

        return view(request, *args, **kwargs)

    return wrapper


class LoginRequiredMixin(object):

    @classmethod
    def as_view(cls, *args, **kwargs):
        """
        此处对统一入口视图函数添加装饰，那么当前视图类里面对所有视图方法都被添加装饰了！
        """
        # 1、获取统一的入口视图函数
        view = super().as_view(*args, **kwargs)
        # 2、对该视图函数添加装饰并返回
        view = login_required(view)
        return view
