from django.urls import path,re_path
from . import views


urlpatterns = [
    path('image_codes/<uuid:uuid>/', views.ImageCodeView.as_view()),
    path('sms_codes/<mobile:mobile>/', views.SMSCodeView.as_view()),

]
