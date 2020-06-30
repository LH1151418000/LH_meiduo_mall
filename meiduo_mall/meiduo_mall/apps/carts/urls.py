from django.urls import path
from . import views


urlpatterns = [
    path('carts/', views.CartsView.as_view()),
    path('carts/selection/', views.CartSelectAllView.as_view()),

]
