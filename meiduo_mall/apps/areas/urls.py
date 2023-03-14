from django.urls import path
from apps.areas.views import AreasView, SubAreasView, UpdateDestroyAddressView, DefaultAddressView, \
    UpdateTitleAddressView, CreateAddressView, AddressView

urlpatterns = [
    path('areas/', AreasView.as_view()),
    path('areas/<pk>/', SubAreasView.as_view()),
    path('addresses/create/', CreateAddressView.as_view()),
    path('addresses/', AddressView.as_view()),
    path('addresses/<address_id>/', UpdateDestroyAddressView.as_view()),
    path('addresses/<address_id>/default/', DefaultAddressView.as_view()),
    path('addresses/<address_id>/title/', UpdateTitleAddressView.as_view()),

]
