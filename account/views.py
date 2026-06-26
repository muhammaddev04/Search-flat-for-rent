from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from random import randint
from .models import EmailConfirm, User


def send_email_confirmation(user):
    code = randint(100000, 999999)
    EmailConfirm.objects.update_or_create(
        user=user,
        defaults={'code': str(code)}
    )
    try:
        send_mail(
            subject='Тасдиқи почта',
            message=f'{user.username}, хуш омадед! Рамзи тасдиқи шумо: {code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception as e:
        print(e, '=== Хатои фиристодани почта ===')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')

        if not username or not email or not password1 or not password2 or not role:
            return render(request, 'register.html', {'error': 'Лутфан ҳамаи майдонҳоро пур кунед'})

        if password1 != password2:
            return render(request, 'register.html', {'error': 'Рамзҳо мувофиқ нестанд'})

        elif role not in ['landlord', 'tenant']:
            # Муҳофизат: admin ҳаргиз аз ин форм қабул намешавад
            return render(request, 'register.html', {'error': 'Нақши нодуруст'})

        elif User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Ин номи корбар аллакай вуҷуд дорад'})

        elif User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Ин почта аллакай сабт шудааст'})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            role=role,
            is_active=False,
        )

        send_email_confirmation(user)
        return render(request, 'confirm.html', {'user': user})

    return render(request, 'register.html')


def confirm_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        code = request.POST.get('code')

        user = User.objects.filter(email=email).first()
        if not user:
            return render(request, 'confirm.html', {'error': 'Почтаи нодуруст'})

        confirm_code = EmailConfirm.objects.filter(user=user).first()

        if not confirm_code or code != confirm_code.code:
            return render(request, 'confirm.html', {'error': 'Рамзи нодуруст', 'user': user})

        user.is_active = True
        user.save()
        confirm_code.delete()  # рамз як бора истифода мешавад
        return redirect('login')

    return render(request, 'confirm.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if not user:
            return render(request, 'login.html', {'error': 'Номи корбар ё рамз нодуруст аст ё сабти ном накардаед!'})

        if not user.is_active:
            return render(request, 'login.html', {'error': 'Аввал почтаи худро тасдиқ кунед'})

        login(request, user)
        return redirect('home')

    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        request.user.bio = request.POST.get('bio', request.user.bio)
        request.user.phone_number = request.POST.get('phone_number', request.user.phone_number)

        photo = request.FILES.get('photo')
        if photo:
            request.user.photo = photo

        request.user.save()
        return redirect('profile')

    return render(request, 'profile.html')