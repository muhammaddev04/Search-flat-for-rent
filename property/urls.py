from django.urls import path
from . import views

urlpatterns = [
   
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('search/', views.property_search, name='property_search'),
    path('property/<int:pk>/', views.property_detail, name='property_detail'),

    
    path('my-properties/', views.property_list, name='property_list'),
    path('create-property/', views.create_property, name='create_property'),
    path('update-property/<int:pk>/', views.update_property, name='update_property'),
    path('delete-property/<int:pk>/', views.delete_property, name='delete_property'),

    path('propertyimages/', views.propertyimage_list, name='propertyimages_list'),
    path('create-propertyimages/', views.create_propertyimage, name='create_propertyimages'),
    path('update-propertyimages/<int:pk>/', views.update_propertyimage, name='update_propertyimages'),
    path('delete-propertyimages/<int:pk>/', views.delete_propertyimage, name='delete_propertyimages'),

    
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('toggle-favorite/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
    path('delete-favorite/<int:pk>/', views.delete_favorite, name='delete_favorite'),

    path('ask-groq/', views.ask_groq_view, name='ask_groq'),
]