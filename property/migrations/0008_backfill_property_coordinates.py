import random

from django.db import migrations


# Маркази ҳар шаҳри Тоҷикистон (координатаҳои воқеии ҷуғрофӣ, на маълумоти сохта).
# Барои амволе, ки координата надорад, як нуқтаи наздик ба маркази шаҳраш
# бо ҷиттери хурди тасодуфӣ (то ~1.5 км) таъин карда мешавад, то нишонаҳо дар
# харита ба ҳам ланбар нашаванд.
CITY_COORDS = {
    'dushanbe': (38.5598, 68.7870),
    'khujand': (40.2833, 69.6222),
    'kulob': (37.9139, 69.7822),
    'bokhtar': (37.8322, 68.7803),
    'qurghonteppa': (37.8322, 68.7803),
    'istaravshan': (39.9086, 69.0033),
    'konibodom': (40.2900, 70.4200),
    'khorog': (37.4924, 71.5533),
}
DEFAULT_COORDS = CITY_COORDS['dushanbe']


def backfill_coordinates(apps, schema_editor):
    Property = apps.get_model('property', 'Property')
    rng = random.Random(1729)  # тухми собит — натиҷа ҳар бор якхела аст, на тасодуфии вазнин
    for prop in Property.objects.filter(latitude__isnull=True, longitude__isnull=True):
        key = (prop.city or '').strip().lower()
        base_lat, base_lng = CITY_COORDS.get(key, DEFAULT_COORDS)
        jitter_lat = (rng.random() - 0.5) * 0.024   # ≈ ±1.3 км
        jitter_lng = (rng.random() - 0.5) * 0.024
        prop.latitude = round(base_lat + jitter_lat, 6)
        prop.longitude = round(base_lng + jitter_lng, 6)
        prop.save(update_fields=['latitude', 'longitude'])


def noop_reverse(apps, schema_editor):
    # Баргардонидан лозим нест: холӣ кардани координатаҳо маълумоти воқеиро
    # намерезонад (ҳарду майдон nullable ҳастанд), бинобар ин reverse — бе амал.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('property', '0007_alter_favorite_id_alter_message_id_alter_property_id_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_coordinates, noop_reverse),
    ]
