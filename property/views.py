from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Property, Property_Image, Favorite
from .forms import PropertyForm, PropertyImageForm
from django.http import JsonResponse
from django.db.models import Avg
import os
from django.http import JsonResponse
from groq import Groq
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Property, Favorite, Message




load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

# Содда rate-limit барои AI ассистент: ҳар корбар на бештар аз 15 дархост дар як дақиқа.
# Ин пеши сӯхтани GROQ_API_KEY-ро аз тарафи корбарони бераҳм мегирад.
AI_RATE_LIMIT = 15
AI_RATE_WINDOW = 60  # сония

AI_REPLY_LANGUAGES = {
    'tg': 'Tajik',
    'ru': 'Russian',
    'en': 'English',
}

# Калидвожаҳое, ки паёми корбарро ба филтрҳои воқеии Property мепайванданд —
# ин ба AI имкон медиҳад "дастрасии контекстӣ" ба маълумоти БОЗ ба ҷои
# додаҳои статикии frontend дошта бошад.
_CITY_KEYWORDS = ['dushanbe', 'душанбе', 'khujand', 'хуҷанд', 'худжанд', 'kulob', 'кӯлоб', 'куляб', 'bokhtar', 'бохтар']
_TYPE_KEYWORDS = {
    'apartment': ['apartment', 'квартира', 'квартираи', 'flat'],
    'house': ['house', 'ҳавлӣ', 'хонаи', 'дом', 'ҳавлигӣ'],
    'room': ['room', 'ҳуҷра', 'комната'],
}


def _find_relevant_properties(user_message):
    """
    Ҷустуҷӯи сабуки калидвожа дар паёми корбар, то ба AI то 5 эълони ВОҚЕӢ
    аз БОЗ дода шавад — ба ҷои он ки AI маълумотро аз худ тахмин занад.
    """
    text = user_message.lower()
    qs = Property.objects.filter(is_available=True)

    for city in _CITY_KEYWORDS:
        if city in text:
            qs = qs.filter(city__icontains=city.split()[0][:4])
            break

    for ptype, keywords in _TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            qs = qs.filter(property_type=ptype)
            break

    return qs.order_by('-created_at')[:5]


def _format_properties_context(properties):
    if not properties:
        return "No matching properties were found in the database for this query."
    lines = []
    for p in properties:
        lines.append(
            f"- [ID {p.id}] {p.title} | {p.get_property_type_display()} | {p.price} TJS | "
            f"{p.rooms} rooms, {p.area} m² | {p.city or '—'}, {p.district} | "
            f"{'available' if p.is_available else 'not available'} | /property/{p.id}/"
        )
    return "\n".join(lines)


@login_required
def ask_groq_view(request):
    if request.method != 'POST':
        return JsonResponse({'response': 'Метод пуштибонӣ намешавад.'}, status=405)

    # --- rate limiting (ба ҳисоби корбари воридшуда) ---
    from django.core.cache import cache
    cache_key = f'ai_rate_{request.user.pk}'
    request_count = cache.get(cache_key, 0)
    if request_count >= AI_RATE_LIMIT:
        return JsonResponse(
            {'response': 'Шумо занҷираи дархостҳоро зиёд кардед. Лутфан баъд аз як дақиқа кӯшиш кунед.'},
            status=429,
        )
    cache.set(cache_key, request_count + 1, timeout=AI_RATE_WINDOW)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return JsonResponse({'response': 'Хатогӣ: API Key танзим нашудааст.'}, status=500)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'response': 'Дархости нодуруст.'}, status=400)

    user_message = (data.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'response': 'Лутфан паём нависед.'}, status=400)
    if len(user_message) > 2000:
        return JsonResponse({'response': 'Паём хеле дароз аст (макс. 2000 аломат).'}, status=400)

    reply_lang = AI_REPLY_LANGUAGES.get((data.get('lang') or '').lower(), 'Tajik')

    # Дастрасии контекстӣ ба БОЗ — ҷустуҷӯи воқеӣ дар асоси паёми корбар,
    # на такя ба маълумоти статикии frontend.
    relevant_properties = _find_relevant_properties(user_message)
    properties_context = _format_properties_context(relevant_properties)

    client = Groq(api_key=api_key)

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the AI assistant for a real estate platform called Comfort Home."
                        "You assist users ONLY within the real estate system: properties (listings), "
                        "property details, search & filters, users, favorites, images, landlord actions "
                        "(if allowed). You must NOT talk about unrelated topics. Always use real database "
                        "data — you are given a REAL_PROPERTIES context block below with actual current "
                        "listings relevant to the user's message; base your answer on that data and never "
                        "invent or assume missing information. If REAL_PROPERTIES says no matches were "
                        "found, tell the user nothing matched — do not make up a listing. If multiple "
                        f"results exist, summarize briefly (max 5 items). Reply ONLY in {reply_lang}, "
                        "regardless of what language the user wrote in — this is a strict UI-language "
                        "requirement set by the platform, not a translation request. Never mix languages "
                        "in one response. Short, clear, and useful. No long explanations. No storytelling. "
                        "Focus on actions and data. If user asks outside real estate, politely refuse and "
                        "return to platform topic. Do not give personal opinions. Be precise and "
                        "professional. When mentioning a property include: Title, Price, Location, and a "
                        "short 1-2 line description. You are not a general AI — you are a domain-specific "
                        "real estate assistant for Comfort Home.\n\n"
                        f"REAL_PROPERTIES (current matches from the database for this query):\n{properties_context}"
                    )
                },
                {"role": "user", "content": user_message}
            ],
            model="openai/gpt-oss-120b",
        )
        return JsonResponse({'response': chat_completion.choices[0].message.content})
    except Exception:
        return JsonResponse({'response': 'Хатогӣ ҳангоми пайвастшавӣ ба AI. Лутфан баъдтар кӯшиш кунед.'}, status=502)




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


from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Property, Favorite, Message

def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    is_favorited = False
    messages = []


    if request.method == 'POST' and request.user.is_authenticated:

        if 'send_message' in request.POST:
            content = (request.POST.get('content') or '').strip()
            if content:
                Message.objects.create(
                    sender=request.user,
                    receiver=prop.owner,
                    property=prop,
                    content=content
                )
            return redirect('property_detail', pk=pk)

        # Эзоҳ: toggle кардани "дилхоҳ" аллакай дар view-и алоҳида
        # `toggle_favorite` (бо URL-и худаш) иҷро мешавад — ин ҷо такрор буд
        # ва ҳеҷ коре намекард (dead code), бинобар ин бартараф карда шуд.


    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, property=prop).exists()


        messages = Message.objects.filter(property=prop).filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).order_by('timestamp')

    # --- Баҳодиҳии воқеии бозор (Real Market Valuation) ---
    # Миёнаи нарх аз рӯи амволҳои ҳамон шаҳр ва ҳамон навъ (ба ғайр аз худи ин эълон)
    # ҳисоб карда мешавад. Агар маълумоти кофӣ набошад (< 2 эълони монанд),
    # баҳодиҳӣ нишон дода намешавад — на рақами тахминӣ.
    comparables = Property.objects.filter(
        city=prop.city,
        property_type=prop.property_type,
    ).exclude(pk=prop.pk)
    market_stats = comparables.aggregate(avg_price=Avg('price'))
    market_avg = market_stats['avg_price']
    market_count = comparables.count()
    market_diff_pct = None
    if market_avg:
        market_avg = round(market_avg, 2)
        market_diff_pct = round(((prop.price - market_avg) / market_avg) * 100)

    return render(request, 'property_detail.html', {
        'property': prop,
        'is_favorited': is_favorited,
        'messages': messages,
        'market_avg': market_avg,
        'market_count': market_count,
        'market_diff_pct': market_diff_pct,
    })


def properties_map_data(request):
    """
    API-и сабук барои харитаи Leaflet: рӯйхати амволҳои дастрас бо координата
    (JSON). Танҳо GET, кушода барои ҳама (анонимӣ низ), барои он ки харита
    дар саҳифаи асосӣ кор кунад новобаста аз ҳолати вуруд.
    """
    propertys = Property.objects.filter(
        is_available=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).select_related('owner')[:200]

    data = [
        {
            'id': p.id,
            'title': p.title,
            'price': str(p.price),
            'city': p.city or '',
            'district': p.district or '',
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'type': p.get_property_type_display(),
            'url': f'/property/{p.id}/',
            'image': p.images.first().image.url if p.images.first() else None,
        }
        for p in propertys
    ]
    return JsonResponse({'properties': data})
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
        form = PropertyForm(request.POST)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.owner = request.user
            prop.save()
            return redirect('property_list')
        return render(request, 'property_form.html', {'form': form})

    return render(request, 'property_form.html', {'form': PropertyForm()})


@login_required
def update_property(request, pk):
    prop = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=prop)
        if form.is_valid():
            form.save()
            return redirect('property_list')
        return render(request, 'property_form.html', {'form': form, 'property': prop})

    return render(request, 'property_form.html', {'form': PropertyForm(instance=prop), 'property': prop})


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

    if request.method == 'POST':
        form = PropertyImageForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            # Мутмаин мешавем, ки хонаи интихобшуда воқеан ба ҳамин корбар тааллуқ дорад
            prop = get_object_or_404(Property, pk=form.cleaned_data['property'].pk, owner=request.user)
            image = form.save(commit=False)
            image.property = prop
            image.save()
            return redirect('propertyimages_list')
        return render(request, 'propertyimage_form.html', {
            'form': form,
            'propertys': Property.objects.filter(owner=request.user),
        })

    return render(request, 'propertyimage_form.html', {
        'form': PropertyImageForm(owner=request.user),
        'propertys': Property.objects.filter(owner=request.user),
    })


@login_required
def update_propertyimage(request, pk):
    propertyimage = get_object_or_404(Property_Image, pk=pk, property__owner=request.user)

    if request.method == 'POST':
        form = PropertyImageForm(request.POST, request.FILES, instance=propertyimage, owner=request.user)
        if form.is_valid():
            prop = get_object_or_404(Property, pk=form.cleaned_data['property'].pk, owner=request.user)
            image = form.save(commit=False)
            image.property = prop
            image.save()
            return redirect('propertyimages_list')
        return render(request, 'update_propertyimages.html', {'form': form, 'propertyimage': propertyimage})

    return render(request, 'update_propertyimages.html', {
        'form': PropertyImageForm(instance=propertyimage, owner=request.user),
        'propertyimage': propertyimage,
    })


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


@login_required
def landlord_dashboard(request):
    return render(request, 'dashboard/landlord_dashboard.html')