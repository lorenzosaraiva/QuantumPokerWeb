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
	def __init__(self, flop1, flop2, flop3, players, deck):
		self.flop1 = flop1
		self.flop2 = flop2
		self.flop3 = flop3
		self.turn = "Error"
		self.river = "Error"
		self.all_players = players
		self.active_players = len(players)
		self.checked_players = 0
		self.players = players
		self.current_player = 0
		self.game_phases = [0, 1, 2, 3, 4] # 0 - pre-flop, 1 - flop, 2 - turn, 3 - river.
		self.phase = 0
		self.deck = deck
		self.finished = 0
		self.pot = 0
		self.to_pay = 0
	
	def check(self):
		player = self.players[self.current_player]
		response = ""
		if player.current_bet == self.to_pay: # checa se player já cobriu aposta
			self.checked_players = self.checked_players + 1
			response = "Player " + str(self.current_player) + " has checked."
			if self.checked_players == self.active_players: # acabou rodada de apostas
				self.next_phase()
			else: #não acabou a rodada de apostas, passa pro proximo player
				self.next_player()
		else:
			response = "Player has not yet covered all bets."
		return response
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
			self.pot = self.pot + total
			self.checked_players = 1
			self.to_pay = total
			player.current_bet = player.current_bet + total
			player.stack = player.stack - total
			self.next_player()
		#else:
		# player sem dinheiro

	def call (self):
		if self.to_pay == 0:
			return "Nothing to call, either check or raise."
		player = self.players[self.current_player]
		response = "Player " + str(self.current_player) + " "
		total = self.to_pay - player.current_bet
		if player.stack >= total:
			self.pot = self.pot + total
			player.stack = player.stack - total
			player.current_bet = player.current_bet + self.to_pay
			self.checked_players = self.checked_players + 1
			if self.checked_players == self.active_players: # acabou rodada de apostas
				self.next_phase()
			else:
				self.next_player()
			response = response + "has called for " + str(self.to_pay) + " chips."
			return response
		else:
			response = response + "has not enough to cover, so they went all in. NOT IMPLEMENTED YET."
			return response

	def fold (self):
		del self.players[self.current_player]
		self.active_players = self.active_players - 1
		if self.active_players == 1:
			#acabou mão, player ganhou
			self.finish_hand()

	def finish_hand(self):
		# calcular vencedor. pegando sempre o mesmo por enquantop
		winner = 0
		player = self.players[winner]
		player.stack = player.stack + self.pot
		self.pot = 0
		self.phase = 0 
		self.current_player = 0
		self.active_players = len(self.all_players)
		self.checked_players = 0
		self.to_pay = 0
		self.players = []
		self.deck = build_deck()
		for player in self.all_players:
			player.card1 = [Card(compute_draw_card(self.deck), 0)]
			player.card2 = [Card(compute_draw_card(self.deck), 0)]
		self.flop1 = compute_draw_card(self.deck)
		self.flop2 = compute_draw_card(self.deck)
		self.flop3 = compute_draw_card(self.deck)
		self.players = self.all_players
		# dar o dinheiro pro player vencedor e resetar tudo.

	def get_active_player(self):
		return self.players[self.current_player]

	def next_phase(self):        
		self.phase = self.phase + 1
		self.checked_players = 0
		self.to_pay = 0
		self.current_player = 0

		for player in self.players:
			player.current_bet = 0

		if self.phase == 1:
			print("FLOP")
			print("Table:")
			print(self.flop1, end=' ')
			print(self.flop2, end=' ')
			print(self.flop3)

		if self.phase == 2:
			self.turn = compute_draw_card(self.deck)
			print("TURN")
			print("Table")
			print(self.flop1, end=' ')
			print(self.flop2, end=' ')
			print(self.flop3, end=' ')
			print(self.turn)

		if self.phase == 3:
			self.river = compute_draw_card(self.deck)
			print("RIVER")
			print("Table")
			print(self.flop1, end=' ')
			print(self.flop2, end=' ')
			print(self.flop3, end=' ')
			print(self.turn, end=' ')
			print(self.river)

		if self.phase == 4:
			#compute_players(self)
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

def view_deck (request):
	return HttpResponse(cache.get('deck'))

def compute_draw_card (deck):
	deck = cache.get('deck', deck)
	position = random.randint(0, len(deck) - 1)
	card = deck.pop(position)
	cache.set('deck', deck)
	return card

def index (request):
	return HttpResponse(build_deck())

def show_table (request):
	table = cache.get('table')
	response = "" 
	i = 0
	if table.phase >= 1:
		response = response + str(table.flop1) + str(table.flop2) + str(table.flop3)

	if table.phase >= 2:
		response = response + str(table.turn)

	if table.phase == 3:
		response = response + str(table.river)

	response = response + " Pot: " + str(table.pot) + " Active player is " + str(table.current_player) + ".\n"

	for player in table.players:
		response = response + " Player " + str(i) + " has " + str(player.stack) + " chips and "
		response = response + "("
		for card in player.card1:
			response = response + card.name
		response = response + ") ("
		for card in player.card2:
			response = response + card.name
		response = response + ")"
		response = response + " as hand."
		i = i + 1
	return HttpResponse(response)

def build_hand (request):
	deck = build_deck()
	
	player1 = Player(Card(compute_draw_card(deck),0), Card(compute_draw_card(deck),0), cirq.LineQubit.range(10), 1, cirq.Circuit())
	player2 = Player(Card(compute_draw_card(deck),0), Card(compute_draw_card(deck),0), cirq.LineQubit.range(10), 2, cirq.Circuit())

	table = Table(compute_draw_card(deck), compute_draw_card(deck), compute_draw_card(deck), [player1, player2], deck)
	cache.set('table', table)

	
	#response = str(table.flop1) + str(table.flop2) + str(table.flop3) + str(table.pot)
	return HttpResponse("Hand Start!")

def check(request):
	table = cache.get('table')
	response = table.check()
	cache.set('table', table)
	return HttpResponse(response)

def call(request):
	table = cache.get('table')
	table.call()
	cache.set('table', table)
	return HttpResponse("")

def raise_bet(request, amount=100):
	table = cache.get('table')
	table.raise_bet(amount)
	cache.set('table', table)
	return HttpResponse("Player raised")

def draw_card (request):
	return HttpResponse(compute_draw_card(cache.get('deck')))

def quantum_draw (request):
	#Caso o card esteja normal, transforma em qubit 
	table = cache.get('table')
	player = table.get_active_player()
	card = player.card1
	deck = cache.get('deck')
	next_qubit = player.next_qubit1
	offset = 0
	entangle = 0

	if not entangle:
		player.circuit.append(cirq.H(player.qubits[next_qubit + offset]))

	new_cards = []
	for i in range(len(card)):
		card[i].binary_position = (to_bin(i, next_qubit + 1))

	i = 0

	for i in range(pow(2, next_qubit)):

		new_cards.append(Card(compute_draw_card(deck), to_bin((len(card) + i), next_qubit + 1)))
		#print("Testando valores binários:")
		#print(new_cards[i].name, end = ' ')
		#print(new_cards[i].binary_position)

	card = card + new_cards

	if offset == 0:
		player.next_qubit1 = player.next_qubit1 + 1
	else:
		player.next_qubit2 = player.next_qubit2 + 1

	player.card1 = card
	cache.set('table', table)

	return HttpResponse("Player has quantum drawed.")

def resolve_player (player, bits1, bits2):
	if len(player.card1) > 1:
		player.card1 = [player.card1.pop(int(bits1, 2))]

	if len(player.card2) > 1:
		player.card2 = [player.card2.pop(int(bits2, 2))]

def measure_player (player):
	for i in range(player.next_qubit1):
		player.circuit.append(cirq.measure(player.qubits[i]))

	for i in range(player.next_qubit2):
		player.circuit.append(cirq.measure(player.qubits[i + 5]))


def compute_players (table):
	for player in table.players:
		measure_player(player)

	simulator = Simulator()
	for player in table.players:
		result = ''
		if player.next_qubit1 != 0 or player.next_qubit2 != 0:
			result = simulator.run(player.circuit)
		res = str(result)
		bits1 = ''
		bits2 = ''
		bit = ''
		for i in range(len(res)):
			if res[i] == '=':
				bit = bit + str(res[i + 1])

		if player.next_qubit1 > 0:
			bits1 = bit[:player.next_qubit1]
		if player.next_qubit2 > 0:
			bits2 = bit[player.next_qubit1:]

		resolve_player(player, bits1, bits2)

	cache.set('table', table)


def to_bin(x, n=0):
	return format(x, 'b').zfill(n)


