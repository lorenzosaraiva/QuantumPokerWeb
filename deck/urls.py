from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('draw_card', views.draw_card, name='draw_card'),
    path('view_deck', views.view_deck, name='view_deck'),
    path('build_hand', views.build_hand, name='build_hand'),
    path('show_table', views.show_table, name='show_table'),
    path('raise_bet', views.raise_bet, name='raise_bet'),
    path('call', views.call, name='call'),
    path('check', views.check, name='check'),
    path('quantum_draw', views.quantum_draw, name='quantum_draw'),
]