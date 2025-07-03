from django import forms
from django.contrib.auth.models import User
from citas.models import Cliente, Empresa, Cita, DiaLaborable, Servicio

# Formulario para crear usuario
class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña',
            'required': True,
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Usuario',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Correo electrónico',
                'required': True,
            }),
        }

# Formulario para datos del cliente
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['telefono']
        widgets = {
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono',
                'required': True,
            }),
        }

# Formulario para datos de empresa
class EmpresaForm(forms.ModelForm):
    dias_laborables = forms.ModelMultipleChoiceField(
        queryset=DiaLaborable.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        required=False,
        help_text="Seleccione los días laborables"
    )

    class Meta:
        model = Empresa
        fields = ['nombre_empresa', 'nombre_dueno', 'tipo_empresa', 'telefono', 'direccion', 'dias_laborables']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa',
                'required': True,
            }),
            'nombre_dueno': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del dueño',
                'required': True,
            }),
            'tipo_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tipo de empresa',
                'required': True,
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono',
                'required': True,
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección',
                'rows': 3,
                'required': True,
            }),
        }

# Formulario para crear o editar citas
class CitaForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        widget=forms.HiddenInput(),  # Campo oculto pero se envía en POST
        label="Empresa"
    )

    fecha = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'required': True,
        }),
        label="Fecha"
    )

    hora = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
            'required': True,
        }),
        label="Hora"
    )

    servicio = forms.ModelChoiceField(
        queryset=Servicio.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        }),
        empty_label="Seleccione un servicio",
        label="Servicio"
    )

    comentarios = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Comentarios adicionales (opcional)',
            'rows': 3,
        }),
        required=False,
        label="Comentarios (opcional)"
    )

    class Meta:
        model = Cita
        fields = ['empresa', 'fecha', 'hora', 'servicio', 'comentarios']
# Formulario para datos de servicio
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
                'placeholder': 'Descripción del servicio',
                'rows': 3,
                'required': False,
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Precio del servicio',
                'required': True,
                'min': 0,
            }),
            'duracion': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duración en minutos',
                'required': True,
                'min': 1,
            }),
        }
