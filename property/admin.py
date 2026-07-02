from django.contrib import admin
from .models import Property, Property_Image, Favorite, Message


class PropertyImageInline(admin.TabularInline):
    model = Property_Image
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'district', 'price', 'rooms', 'is_available', 'owner', 'created_at')
    list_filter = ('property_type', 'is_available', 'city')
    search_fields = ('title', 'city', 'district', 'owner__username')
    inlines = [PropertyImageInline]


@admin.register(Property_Image)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'image')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'property', 'is_read', 'timestamp')
    list_filter = ('is_read',)