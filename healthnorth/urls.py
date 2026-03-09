"""URLs principales du projet healthnorth."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
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
# Sert les fichiers media en développement (DEBUG=True)
# En production, c'est le serveur web (nginx, etc.) qui gère ça
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)