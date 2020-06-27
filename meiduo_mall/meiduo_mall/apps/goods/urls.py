from django.urls import path
from . import views

urlpatterns = [
    path('list/<category_id>/skus/', views.ListView.as_view()),
    path('hot/<category_id>/', views.HotGoodsView.as_view()),
    path('search/', views.MySearchView()),
]
