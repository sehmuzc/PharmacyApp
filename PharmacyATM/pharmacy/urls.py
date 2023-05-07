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
    path('my_prescriptions/<int:pk>/get_medicine_delivered/', views.get_medicine_delivered, name='get_medicine_delivered'),
    path('prescription_details/<int:pk>/', views.prescription_details, name='prescription_details'),
    path('prescription_transaction/<int:pk>/', views.prescription_transaction, name='prescription_transaction'),
    path('prescription_details/<int:prescription_id>/add_medicine/', views.add_medicine_to_prescription, name='add_medicine_to_prescription'),
    path('qrupload/', views.qr_upload, name='qrupload'),
    path('atm_list/', views.atm_list, name='atm_list'),
    path('atm/<int:pk>/', views.atm_detail, name='atm_detail'),
    path('atm/<int:pk>/medicine_usages/', views.medicine_usages, name='medicine_usages'),
    path('atm/<int:atm_id>/add_medicine/', views.add_medicine_to_atm, name='add_medicine_to_atm'),
    path('medicine_sales/<int:atm_id>/', views.medicine_sales, name='medicine_sales'),
    path('atm/create/', views.create_atm, name='atm_create'),
    path('atm/<int:pk>/update_thresholds/', views.update_thresholds, name='update_thresholds'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)