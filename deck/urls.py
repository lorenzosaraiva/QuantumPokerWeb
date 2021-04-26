from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('draw_card', views.draw_card, name='draw_card'),
    path('view_deck', views.view_deck, name='view_deck'),
    path('build_hand', views.build_hand, name='build_hand'),
    path('build_hand_JSON', views.build_hand_JSON, name='build_hand_JSON'),
    path('show_table', views.show_table, name='show_table'),
    path('raise_bet', views.raise_bet, name='raise_bet'),
    path('raise_JSON', views.raise_JSON, name='raise_JSON'),
    path('call', views.call, name='call'),
    path('call_JSON', views.call_JSON, name='call_JSON'),
    path('check', views.check, name='check'),
    path('check_JSON', views.check_JSON, name='check_JSON'),
    path('quantum_draw', views.quantum_draw, name='quantum_draw'),
    path('calculate_hand', views.calculate_hand, name='calculate_hand'),
    path('test', views.test, name='test'),
]