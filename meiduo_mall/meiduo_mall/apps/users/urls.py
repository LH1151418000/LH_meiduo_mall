from django.urls import path
from . import views

urlpatterns = [
    path('usernames/<username:username>/count/', views.UserCountView.as_view()),
    path('mobiles/<mobile:mobile>/count/', views.MobileCountView.as_view()),
    path('register/', views.RegisterView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogOutView.as_view()),
    path('info/', views.UserInfoView.as_view()),

]