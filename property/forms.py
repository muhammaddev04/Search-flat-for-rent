from django import forms
from .models import Property, Property_Image, Message
from django.forms.widgets import ClearableFileInput


class PropertyForm(forms.ModelForm):
    """
    Ин форма ҷои пуркунии дастии ҳар майдон (request.POST.get('title') ва ғайра)
    дар create_property / update_property-ро мегирад. Django худаш:
      - навъҳои маълумот (price -> Decimal, rooms -> int) месанҷад
      - хатогиҳоро бо забони фаҳмо бармегардонад
      - аз SQL Injection тавассути ORM муҳофизат мекунад
    """
    class Meta:
        model = Property
        fields = [
            'title', 'description', 'property_type', 'price', 'rooms',
            'area', 'floor', 'city', 'district', 'address_details',
            'amenities', 'is_available', 'latitude', 'longitude',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'address_details': forms.Textarea(attrs={'rows': 3}),
            'amenities': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Масалан: интернет, кондитсионер, паркинг...'}),
            'latitude': forms.NumberInput(attrs={'step': 'any', 'placeholder': '38.5598'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'placeholder': '68.7870'}),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price is None or price <= 0:
            raise forms.ValidationError('Нарх бояд аз сифр зиёд бошад.')
        return price

    def clean_rooms(self):
        rooms = self.cleaned_data['rooms']
        if rooms is None or rooms <= 0:
            raise forms.ValidationError('Шумораи ҳуҷраҳо бояд ҳадди ақал 1 бошад.')
        return rooms


class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = Property_Image
        fields = ['property', 'image']

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields['property'].queryset = Property.objects.filter(owner=owner)



class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultiImageUploadForm(forms.Form):
    images = forms.FileField(
        widget=MultipleFileInput(),
        required=False,
    )


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Паёми худро нависед...',
            }),
        }
