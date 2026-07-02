from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('confirm/', views.confirm_email, name='confirm_email'),
    path('resend-confirmation/', views.resend_confirmation, name='resend_confirmation'),  # НАВ
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]