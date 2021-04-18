from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('draw_card', views.draw_card, name='draw_card'),
    path('view_deck', views.view_deck, name='view_deck'),
]