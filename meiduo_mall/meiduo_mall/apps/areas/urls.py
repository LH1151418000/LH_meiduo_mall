from django.urls import path, re_path
from . import views

urlpatterns = [
    path('areas/', views.ProvinceAreasView.as_view()),
    re_path(r'^areas/(?P<pk>[1-9]\d+)/$', views.SubAreasView.as_view()),

]
