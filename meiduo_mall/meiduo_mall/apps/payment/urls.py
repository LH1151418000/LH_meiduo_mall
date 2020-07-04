from django.urls import path, re_path
from . import views


urlpatterns = [
    path('payment/<order_id>/', views.PaymentView.as_view()),
    # path('payment/status/', views.PaymentStatusView.as_view()),
    re_path(r'^payment/status/$', views.PaymentStatusView.as_view()),

]
