from django.shortcuts import render
from django.http import HttpResponse
import numpy as np
import random
import cirq
import math
import uuid
from django.core.cache import cache

from cirq import Simulator

class Card():
    def __init__(self, name, binary_position): 
        self.name = name
        self.binary_position = binary_position

class Player():
    def __init__(self, card1, card2, qubits, number, circuit):
        self.card1 = [card1]
        self.card2 = [card2]
        self.qubits = qubits
        self.next_qubit1 = 0
        self.next_qubit2 = 0
        self.number = number
        self.circuit = circuit
        self.entangled = []
        self.next_entangle = 0

class Table():
    def __init__(self, flop1, flop2, flop3, total_players, players, deck):
        self.flop1 = flop1
        self.flop2 = flop2
        self.flop3 = flop3
        self.turn = "Error"
        self.river = "Error"
        self.total_players = total_players
        self.checked_players = 0
        self.players = players
        self.game_phases = [0, 1, 2, 3, 4] # 0 - pre-flop, 1 - flop, 2 - turn, 3 - river.
        self.current_phase = 0
        self.deck = deck
        self.finished = 0
    
     def check(self):
        self.checked_players = self.checked_players + 1
        if self.checked_players == self.total_players:
            self.next_phase()


    def next_phase(self):        
        self.current_phase = self.current_phase + 1
        self.checked_players = 0
        if self.current_phase == 1:
            print("FLOP")
            print("Table:")
            print(self.flop1, end=' ')
            print(self.flop2, end=' ')
            print(self.flop3)

        if self.current_phase == 2:
            self.turn = draw_card(self.deck)
            print("TURN")
            print("Table")
            print(self.flop1, end=' ')
            print(self.flop2, end=' ')
            print(self.flop3, end=' ')
            print(self.turn)

        if self.current_phase == 3:
            self.river = draw_card(self.deck)
            print("RIVER")
            print("Table")
            print(self.flop1, end=' ')
            print(self.flop2, end=' ')
            print(self.flop3, end=' ')
            print(self.turn, end=' ')
            print(self.river)

        if self.current_phase == 4:
            self.finish_hand()


def build_deck():
    numbers=list(range(2,11))
    numbers.append('J')
    numbers.append('Q')
    numbers.append('K')
    numbers.append('A')
    suits = ['♡','♠','♣','♢']
    deck = []
    for i in numbers:
        for s in suits:
            card = str(i)+s+ " "
            deck.append(card)
    #print(deck)
    #print(len(deck))
    #deck_id = str(uuid.uuid4())
    cache.set('deck', deck)
    return deck 

def view_deck(request):
    return HttpResponse(cache.get('deck'))

def compute_draw_card(deck):
    position = random.randint(0, len(deck) - 1)
    card = deck.pop(position)
    cache.set('deck', deck)
    return card

def index(request):
    return HttpResponse(build_deck())

def draw_card(request):
    return HttpResponse(compute_draw_card(cache.get('deck')))

