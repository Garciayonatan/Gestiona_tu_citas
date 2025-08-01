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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deshabilitar empresa para que no se pueda cambiar al editar
        self.fields['empresa'].disabled = True


# Formulario para crear o editar servicios

#class ServicioForm(forms.ModelForm):
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


class EditarCitaForm(forms.ModelForm):
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
        fields = ['fecha', 'hora']  # empresa NO va aquí

    # Ya no necesitas __init__ para deshabilitar empresa porque no está en el form


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
                'placeholder': 'Descripción del servicio (máx. 120 caracteres)',
                'maxlength': 120,  # Limita visualmente en el navegador
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

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion', '')
        if len(descripcion) > 120:
            raise forms.ValidationError("La descripción no debe superar los 120 caracteres.")
        return descripcion
    

#borrar si no funciona ahora mismo
class EditarEmpresaForm(forms.ModelForm):
    username = forms.CharField(label='Nombre de Usuario', max_length=150)
    email = forms.EmailField(label='Correo Electrónico')

    class Meta:
        model = Empresa
        fields = ['username', 'email', 'nombre_empresa', 'nombre_dueno', 'tipo_empresa', 'direccion', 'telefono']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.user_instance = user  # guarda referencia al usuario actual

        # Inicializar campos username y email si se pasa el usuario
        if self.user_instance:
            self.fields['username'].initial = self.user_instance.username
            self.fields['email'].initial = self.user_instance.email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Excluir el usuario actual al verificar si ya existe
        if User.objects.exclude(pk=self.user_instance.pk).filter(username=username).exists():
            raise forms.ValidationError("❌ Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Excluir el usuario actual al verificar si ya existe el email
        if User.objects.exclude(pk=self.user_instance.pk).filter(email=email).exists():
            raise forms.ValidationError("❌ Este correo electrónico ya está en uso.")
        return email

    def save(self, commit=True):
        empresa = super().save(commit=False)

        # Actualizar el usuario vinculado
        if self.user_instance:
            self.user_instance.username = self.cleaned_data.get('username')
            self.user_instance.email = self.cleaned_data.get('email')
            if commit:
                self.user_instance.save()

        if commit:
            empresa.user = self.user_instance  # aseguramos que esté asignado
            empresa.save()
            self.save_m2m()

        return empresa

#class EditarEmpresaForm(forms.ModelForm):

    class Meta:
        model = Empresa
        fields = ['nombre_empresa', 'nombre_dueno', 'tipo_empresa', 'direccion', 'telefono']