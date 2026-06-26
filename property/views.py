from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Property, Property_Image, Favorite
from django.http import JsonResponse
import os
from django.http import JsonResponse
from groq import Groq
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
import json


load_dotenv()

@csrf_exempt
def ask_groq_view(request):
    if request.method == 'POST':
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            return JsonResponse({'response': 'Хатогӣ: API Key танзим нашудааст.'}, status=500)

        client = Groq(api_key=api_key)
        
        data = json.loads(request.body)
        user_message = data.get('message')
        
        chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "system", 
            "content": (
                "You are an intelligent assistant for the 'Comfort Home' real estate project. "
                "Your primary goal is to help users only with information related to this project (properties, rentals, services). "
                "1. If the user asks about anything unrelated to real estate or 'Comfort Home', politely decline and redirect them back to the project. "
                "2. Detect the user's language automatically. You must respond in the same language the user is using (Tajik, Russian, or English). "
                "3. Be professional, concise, and helpful."
            )
        },
        {"role": "user", "content": user_message}
    ],
            model="openai/gpt-oss-120b",
        )
        return JsonResponse({'response': chat_completion.choices[0].message.content})




@login_required
def home(request):
    propertys = Property.objects.all()
    favorite_property_ids = []
    
    if request.user.is_authenticated:
        favorite_property_ids = Favorite.objects.filter(user=request.user).values_list('property_id', flat=True)

    
    city = request.GET.get('q')
    if city and isinstance(city, str):
        propertys = propertys.filter(city__icontains=city.strip())

    district = request.GET.get('qu')
    if district and isinstance(district, str):
        propertys = propertys.filter(district__icontains=district.strip())

    min_price = request.GET.get('min_price')
    if min_price:
        propertys = propertys.filter(price__gte=min_price)

    max_price = request.GET.get('max_price')
    if max_price:
        propertys = propertys.filter(price__lte=max_price)

    return render(request, 'home.html', {'propertys': propertys, 'favorite_property_ids': favorite_property_ids})

@login_required
def about(request):
    return render(request, 'about.html')

@login_required
def property_search(request):
    """
    Саҳифаи ҷустуҷӯи ҷамъиятӣ — ҲАМАИ хонаҳои дастрасро нишон медиҳад
    (на танҳо хонаҳои худи корбар). Барои tenant/landlord/анонимӣ кушода аст.
    """
    propertys = Property.objects.filter(is_available=True)

    city = request.GET.get('city')
    if isinstance(city, str):
        city = city.strip()
    if city:
        propertys = propertys.filter(city__icontains=city)

    district = request.GET.get('district')
    if isinstance(district, str):
        district = district.strip()
    if district:
        propertys = propertys.filter(district__icontains=district)

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        propertys = propertys.filter(price__range=(min_price, max_price))
    elif min_price:
        propertys = propertys.filter(price__gte=min_price)
    elif max_price:
        propertys = propertys.filter(price__lte=max_price)

    property_type = request.GET.get('property_type')
    if property_type:
        propertys = propertys.filter(property_type=property_type)

    return render(request, 'property_search.html', {
        'propertys': propertys.order_by('-created_at'),
    })


def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, property=prop).exists()
    return render(request, 'property_detail.html', {
        'property': prop,
        'is_favorited': is_favorited,
    })


@login_required
def property_list(request):

    if not request.user.is_authenticated or request.user.role not in ('landlord', 'admin'):
        return redirect('home')
   
    propertys = Property.objects.filter(owner=request.user)

   
    city = request.GET.get('q')
    if city and isinstance(city, str):
        propertys = propertys.filter(city__icontains=city.strip())

    district = request.GET.get('qu')
    if district and isinstance(district, str):
        propertys = propertys.filter(district__icontains=district.strip())

   
    return render(request, 'property_search.html', {'propertys': propertys})


@login_required
def create_property(request):
    if not request.user.is_authenticated or request.user.role not in ('landlord', 'admin'):
        return redirect('home')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')  
        property_type = request.POST.get('property_type')
        price = request.POST.get('price')
        rooms = request.POST.get('rooms')
        area = request.POST.get('area')
        floor = request.POST.get('floor')
        city = request.POST.get('city')
        district = request.POST.get('district')
        address_details = request.POST.get('address_details')
        amenities = request.POST.get('amenities')
        is_available = request.POST.get('is_available') == 'on'

        
        if not all([title, property_type, price, rooms, area, city, district, address_details]):
            return render(request, 'property_form.html', {
                'error': 'Лутфан ҳамаи майдонҳои асосиро пур кунед!'
            })

        try:
           
            Property.objects.create(
                title=title,
                description=description,
                property_type=property_type,
                price=float(price) if price else 0,  
                rooms=int(rooms) if rooms else 1,    
                area=float(area) if area else 0,      
                floor=int(floor) if floor else 0,      
                city=city,
                district=district,
                address_details=address_details,
                amenities=amenities,
                is_available=is_available,
                owner=request.user,
            )
            return redirect('property_list')
            
        except Exception as e:
            return render(request, 'property_form.html', {
                'error': f'Хатогӣ ҳангоми захира дар база: {e}'
            })

    return render(request, 'property_form.html')


@login_required
def update_property(request, pk):
    prop = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        prop.title = request.POST.get('title')
        prop.description = request.POST.get('description')
        prop.property_type = request.POST.get('property_type')
        prop.price = request.POST.get('price')
        prop.rooms = request.POST.get('rooms')
        prop.area = request.POST.get('area')
        prop.floor = request.POST.get('floor')
        prop.city = request.POST.get('city')
        prop.district = request.POST.get('district')
        prop.address_details = request.POST.get('address_details')
        prop.amenities = request.POST.get('amenities')
        prop.is_available = request.POST.get('is_available') == 'on'

        prop.save()
        return redirect('property_list')
    return render(request, 'property_form.html', {'property': prop})


@login_required
def delete_property(request, pk):
    prop = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        prop.delete()
        return redirect('property_list')
    return render(request, 'property_confirm_delete.html', {'property': prop})


# ---------------------------------------------------------
# Аксҳои хона (Property_Image)
# ---------------------------------------------------------

@login_required
def propertyimage_list(request):
    """Аксҳои марбут ба хонаҳои худи соҳибхона."""
    propertyimages = Property_Image.objects.filter(property__owner=request.user)

    query = request.GET.get('q')
    if isinstance(query, str):
        query = query.strip()
    if query:
        propertyimages = propertyimages.filter(property__title__icontains=query)

    return render(request, 'propertyimage_list.html', {'propertyimages': propertyimages})


@login_required
def create_propertyimage(request):
    if not request.user.is_authenticated or request.user.role not in ('landlord', 'admin'):
        return redirect('home')
        # return HttpResponse('Танҳо соҳибхона метавонад сурат илова кунад', status=403)
        


    if request.method == 'POST':
        property_id = request.POST.get('property')
        image = request.FILES.get('image')

        if not property_id or not image:
            return render(request, 'propertyimage_form.html', {
                'error': 'Лутфан хона ва аксро интихоб кунед',
                'propertys': Property.objects.filter(owner=request.user),
            })

        # Мутмаин шавем хона тааллуқ дорад ба ҳамин корбар
        prop = get_object_or_404(Property, pk=property_id, owner=request.user)

        Property_Image.objects.create(
            property=prop,
            image=image,
        )

        return redirect('propertyimages_list')

    return render(request, 'propertyimage_form.html', {
        'propertys': Property.objects.filter(owner=request.user),
    })


@login_required
def update_propertyimage(request, pk):
    propertyimage = get_object_or_404(Property_Image, pk=pk, property__owner=request.user)

    if request.method == 'POST':
        property_id = request.POST.get('property')
        if property_id:
            prop = get_object_or_404(Property, pk=property_id, owner=request.user)
            propertyimage.property = prop

        new_image = request.FILES.get('image')
        if new_image:
            propertyimage.image = new_image

        propertyimage.save()
        return redirect('propertyimages_list')

    return render(request, 'update_propertyimages.html', {'propertyimage': propertyimage})


@login_required
def delete_propertyimage(request, pk):
    propertyimage = get_object_or_404(Property_Image, pk=pk, property__owner=request.user)

    if request.method == 'POST':
        propertyimage.delete()
        return redirect('propertyimages_list')
    return render(request, 'delete_propertyimages.html', {'propertyimage': propertyimage})


# ---------------------------------------------------------
# Дилхоҳ (Favorite) — танҷо барои tenant/корбари воридшуда
# ---------------------------------------------------------


@login_required
def favorite_list(request):
    if not request.user.is_authenticated or request.user.role not in ('tenant', 'admin'):
        return redirect('home')
        
    favorites = Favorite.objects.filter(user=request.user).select_related('property')
    
   
    favorite_properties = [fav.property for fav in favorites]
    
    
    return render(request, 'favorites_list.html', {
        'favorite_properties': favorite_properties
    })

@login_required
def toggle_favorite(request, pk):
    if request.method == 'POST':
        property_obj = get_object_or_404(Property, pk=pk)
        favorite, created = Favorite.objects.get_or_create(user=request.user, property=property_obj)
        
        if not created:
            favorite.delete()
            status = 'removed'
        else:
            status = 'added'
            
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': status})
            
        
        return redirect(request.META.get('HTTP_REFERER', 'home'))
        
    return redirect('home')


@login_required
def delete_favorite(request, pk):
    favorite = get_object_or_404(Favorite, pk=pk, user=request.user)

    if request.method == 'POST':
        favorite.delete()
        return redirect('favorite_list')
    return render(request, 'delete_favorites.html', {'favorite': favorite})