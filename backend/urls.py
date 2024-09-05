from django.urls import path
from .views import *

urlpatterns = [
    path('', view_dashboard, name='dashboard'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('gallery/', upload_image, name='gallery'),
    path('delete_image/<int:image_id>/', delete_image, name='delete_image'),
    path('services/', service_operations, name='services'),
    path('delete_service/<int:service_id>/', delete_service, name='delete_service'),
    path('accounts/', view_accounts, name='accounts'),
    path('delete_user/<int:user_id>/', delete_user, name='delete_user'),
    path('user/<int:user_id>/', user_details, name='user_details'),

    path('delete_appointment/<int:appointment_id>/', delete_appointment, name='delete_appointment'),
    path('update_appointment_status/<int:appointment_id>/', update_appointment_status,
         name='update_appointment_status'),

    path('get_available_time_slots/', get_available_time_slots, name='get_available_time_slots'),

]
