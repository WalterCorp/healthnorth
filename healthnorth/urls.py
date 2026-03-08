"""URLs principales du projet healthnorth."""

from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Interface d'administration Django
    path('admin/', admin.site.urls),
    # Page d'accueil
    path('', views.home, name='home'),
    # URLs de l'application accounts
    path('accounts/', include('accounts.urls')),
    # URLs de l'application appointments
    path('appointments/', include('appointments.urls')),
]