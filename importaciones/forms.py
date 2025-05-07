# importaciones/forms.py

from django import forms

class BaseDatosForm(forms.Form):
    BASE_DATOS_CHOICES = [
        ('bd_semilla_starsoft', 'Semilla'),
        ('bd_maxi_starsoft', 'Maximilian'),
        ('bd_trading_starsoft', 'Trading'),
    ]
    base_datos = forms.ChoiceField(choices=BASE_DATOS_CHOICES, label='Selecciona la empresa')
