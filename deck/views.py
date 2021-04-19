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
		self.current_bet = 0
		self.stack = 1000

class Table():
	def __init__(self, flop1, flop2, flop3, total_players, players, deck):
		self.flop1 = flop1
		self.flop2 = flop2
		self.flop3 = flop3
		self.turn = "Error"
		self.river = "Error"
		self.total_players = total_players
		self.active_players = total_players
		self.checked_players = 0
		self.players = players
		self.current_player = 0
		self.game_phases = [0, 1, 2, 3, 4] # 0 - pre-flop, 1 - flop, 2 - turn, 3 - river.
		self.current_phase = 0
		self.deck = deck
		self.finished = 0
		self.current_pot = 0
		self.to_pay = 0
	
	def check(self):
		player = self.players[self.current_player]
		ret = "Player " + str(self.current_player) + " has checked."
		if player.current_bet == self.to_pay: # checa se player já cobriu aposta
			self.checked_players = self.checked_players + 1
			if self.checked_players == self.active_players: # acabou rodada de apostas
				self.next_phase()
			else: #não acabou a rodada de apostas, passa pro proximo player
				self.next_player()
		return ret
		#else:
			# exception > players não pagou a aposta. Na real essa checagem idealmente seria feita a cada começo 
			# de turno do player e desativaria o botão Check.

	def next_player(self):
		self.current_player = self.current_player + 1
		if self.current_player == len(self.players):
			self.current_player = 0 

	def raise_bet(self, amount):
		player = self.players[self.current_player]
		total = amount + self.to_pay
		if player.stack >= amount + self.to_pay:
			self.current_pot = self.current_pot + total
			self.checked_players = 0
			self.to_pay = total
			player.current_bet = player.current_bet + total
			player.stack = player.stack - total
			self.next_player()
		#else:
		# player sem dinheiro

	def call (self):
		player = self.players[self.current_player]
		if player.stack >= self.to_pay:
			self.current_pot = self.current_pot + self.to_pay
			player.current_bet = self.to_pay
			self.next_player()
		#else:
		# player sem dinheiro, lidar com o caso do All In depois ()

	def fold (self):
		del self.players[self.current_player]
		self.active_players = self.active_players - 1
		if self.active_players == 1:
			#acabou mão, player ganhou
			finish_hand(self)

	def finish_hand(self):
		print("a")
		# dar o dinheiro pro player vencedor e resetar tudo.

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
			self.finish_hand(self)


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
	if deck == None:
		deck = build_deck()
	position = random.randint(0, len(deck) - 1)
	card = deck.pop(position)
	cache.set('deck', deck)
	return card

def index(request):
	return HttpResponse(build_deck())

def show_table(request):
	table = cache.get('table')
	response = str(table.flop1) + str(table.flop2) + str(table.flop3) + " Pot: " + str(table.current_pot) + " Active player is " + str(table.current_player) + ".\n"
	i = 0
	for player in table.players:
		response = response + " Player " + str(i) + " has " + str(player.stack) + " chips. \n"
		i = i + 1
	return HttpResponse(response)

def build_hand(request):
	deck = cache.get('deck')

	player1 = Player(Card(compute_draw_card(deck),0), Card(compute_draw_card(deck),0), cirq.LineQubit.range(10), 1, cirq.Circuit())
	player2 = Player(Card(compute_draw_card(deck),0), Card(compute_draw_card(deck),0), cirq.LineQubit.range(10), 2, cirq.Circuit())

	table = Table(compute_draw_card(deck), compute_draw_card(deck), compute_draw_card(deck), 2, [player1, player2], deck)
	cache.set('table', table)
	
	response = str(table.flop1) + str(table.flop2) + str(table.flop3) + str(table.current_pot)
	return HttpResponse(response)

def check(request):
	table = cache.get('table')
	response = table.check()
	cache.set('table', table)
	return HttpResponse(response)

def raise_bet(request, amount=100):
	table = cache.get('table')
	table.raise_bet(amount)
	cache.set('table', table)
	return HttpResponse("")

def draw_card(request):
	return HttpResponse(compute_draw_card(cache.get('deck')))

