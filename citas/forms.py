from django import forms
from django.contrib.auth.models import User
from .models import Cliente, Empresa, Cita, Servicio


# Formulario de registro de usuario
class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Contraseña'
        }),
        label="Contraseña"
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre de usuario'
        }),
        label="Nombre de Usuario"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Correo electrónico'
        }),
        label="Correo Electrónico"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']


# Formulario de registro de cliente
class ClienteForm(forms.ModelForm):
    nombre_completo = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre Completo'
        }),
        label="Nombre Completo"
    )
    telefono = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Teléfono'
        }),
        label="Teléfono"
    )
    direccion = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Dirección'
        }),
        required=False,
        label="Dirección"
    )
    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control'
        }),
        required=False,
        label="Fecha de Nacimiento"
    )
    genero = forms.ChoiceField(
        choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label="Género"
    )

    class Meta:
        model = Cliente
        fields = ['nombre_completo', 'telefono', 'direccion', 'fecha_nacimiento', 'genero']


# Formulario de registro de empresa
class EmpresaForm(forms.ModelForm):
    nombre_empresa = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre de la Empresa'
        }),
        label="Nombre de la Empresa"
    )
    nombre_dueno = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre del Dueño'
        }),
        label="Nombre del Dueño"
    )
    tipo_empresa = forms.ChoiceField(
        choices=[("", "Selecciona el tipo de empresa")] + list(Empresa._meta.get_field('tipo_empresa').choices),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo de Empresa"
    )
    telefono = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Teléfono'
        }),
        label="Teléfono"
    )
    direccion = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Dirección'
        }),
        required=False,
        label="Dirección"
    )

    class Meta:
        model = Empresa
        fields = ['nombre_empresa', 'nombre_dueno', 'tipo_empresa', 'telefono', 'direccion']


# Formulario para agendar citas
class CitaForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Empresa"
    )
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha"
    )
    hora = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label="Hora"
    )

    class Meta:
        model = Cita
        fields = ['empresa', 'fecha', 'hora']


# Formulario para crear o editar servicios
class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'precio', 'duracion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del servicio',
                'required': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del servicio',
                'required': False,
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Precio del servicio',
                'min': 0,
                'required': True,
            }),
            'duracion': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duración en minutos',
                'min': 1,
                'required': True,
            }),
        }

