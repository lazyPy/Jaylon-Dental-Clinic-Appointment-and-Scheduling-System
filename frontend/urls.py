from django.urls import path

from backend.views import get_available_time_slots
from .views import *

urlpatterns = [
    path('', view_client_dashboard, name='client_dashboard'),
    path('profile/', view_client_profile, name='client_profile'),
    path('login/', client_login, name='client_login'),
    path('register/', client_register, name='client_register'),
    path('verify-email/<str:token>/', verify_email, name='verify_email'),
    path('logout/', client_logout, name='client_logout'),

    path('get_available_time_slots/', get_available_time_slots, name='client_get_available_time_slots'),
    ]
