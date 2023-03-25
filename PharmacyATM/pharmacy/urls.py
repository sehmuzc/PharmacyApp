from django.urls import path
from django.urls import re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

from .import views

urlpatterns = [
    path('', views.home, name='pharmacy-home'),
    path('give_prescription/', views.give_prescription, name='give_prescription'),
    path('patient_prescriptions/<int:pk>/', views.patient_prescriptions, name='patient_prescriptions'),
    path('my_prescriptions/', views.my_prescriptions, name='my_prescriptions'),
    path('my_prescriptions/<int:pk>/get_medicine_from_atm/', views.get_medicine_from_atm, name='get_medicine_from_atm'),
    path('prescription_details/<int:pk>/', views.prescription_details, name='prescription_details'),
    path('prescription_transaction/<int:pk>/', views.prescription_transaction, name='prescription_transaction'),
    path('prescription_details/<int:prescription_id>/add_medicine/', views.add_medicine_to_prescription, name='add_medicine_to_prescription'),
    path('qrupload/', views.qr_upload, name='qrupload'),
    path('atm_list/', views.atm_list, name='atm_list'),
    path('atm/<int:pk>/', views.atm_detail, name='atm_detail'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)