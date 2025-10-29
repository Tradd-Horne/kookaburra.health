"""
URL configuration for Django project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import index, lander

urlpatterns = [
    path('', index, name='index'),
    path('lander/', lander, name='lander'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.users.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('api/', include('api.urls')),
]

# Debug toolbar
if settings.DEBUG:
    import debug_toolbar
    
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Let Django's staticfiles app handle static files in development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()