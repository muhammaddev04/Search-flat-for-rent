from django.contrib import admin
from .models import Property,Property_Image,Favorite

admin.site.register([Property,Property_Image,Favorite])
