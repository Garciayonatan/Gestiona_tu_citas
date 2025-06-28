from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cliente, Empresa

def login_view(request):
    if request.method == 'POST':
        # Obtén los datos del formulario
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Autentica al usuario
        user = authenticate(request, username=username, password=password)
        if user:
            # Inicia sesión si la autenticación es exitosa
            login(request, user)

            # Redirigir según el tipo de usuario
            if hasattr(user, 'cliente'):
                messages.success(request, 'Iniciaste sesión como cliente exitosamente.')
                return redirect('app:cliente_panel')  # Redirige al panel del cliente
            elif hasattr(user, 'empresa'):
                messages.success(request, 'Iniciaste sesión como empresa exitosamente.')
                return redirect('app:empresa_panel')  # Redirige al panel de la empresa
            else:
                messages.warning(request, 'No se pudo determinar el tipo de usuario.')
                return redirect('app:home')  # Redirección predeterminada en caso de error
        else:
            # Si la autenticación falla, muestra un mensaje de error
            messages.error(request, 'Usuario o contraseña incorrectos.')

    # Renderiza la página de inicio de sesión
    return render(request, 'app/login.html')

@login_required(login_url='app:login')
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('app:login')

@login_required(login_url='app:login')
def cliente_panel(request):
    cliente = get_object_or_404(Cliente, user=request.user)
    return render(request, 'app/cliente_panel.html', {'cliente': cliente})

@login_required(login_url='app:login')
def empresa_panel(request):
    empresa = get_object_or_404(Empresa, user=request.user)
    return render(request, 'app/empresa_panel.html', {'empresa': empresa})
