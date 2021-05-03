from django.shortcuts import render
from django.http import HttpResponse
import numpy as np
import random
import cirq
import math
import uuid
import json
from django.core.cache import cache
from cirq import Simulator
from pokereval.card import Card
from pokereval.hand_evaluator import HandEvaluator
from django.template import loader
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt


class _Card():
	def __init__(self, name, power, suit):
		self.name = name
		self.binary_position = 0
		self.power = power
		self.suit = suit


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

	def get_card1(self):
		ret = ""
		for card in self.card1:
			ret = ret + str(card.name)
		return ret

	def get_card2(self):
		ret = ""
		for card in self.card2:
			ret = ret + str(card.name)
		return ret

class Table():
	def __init__(self, flop1, flop2, flop3, players, deck):
		self.flop1 = flop1
		self.flop2 = flop2
		self.flop3 = flop3
		self.turn = "Error"
		self.river = "Error"
		self.cards = [flop1, flop2, flop3]
		self.all_players = players[:]
		self.active_players = len(players)
		self.checked_players = 0
		self.players = players
		self.current_player = 0
		# 0 - pre-flop, 1 - flop, 2 - turn, 3 - river.
		self.phase = 0
		self.deck = deck
		self.finished = 0
		self.pot = 0
		self.to_pay = 0

	def check (self):
		player = self.players[self.current_player]
		response = ""
		if player.current_bet == self.to_pay:  # checa se player já cobriu aposta
			self.checked_players = self.checked_players + 1
			response = "Player " + str(self.current_player) + " has checked."
			if self.checked_players == self.active_players:  # acabou rodada de apostas
				self.next_phase()
			else:  # não acabou a rodada de apostas, passa pro proximo player
				self.next_player()
		else:
			response = "Player has not yet covered all bets."
		return response
		# else:
		# exception > players não pagou a aposta. Na real essa checagem idealmente seria feita a cada começo
		# de turno do player e desativaria o botão Check.

	def check_JSON(self):
		player = self.players[self.current_player]
		response = ""
		response_data = {}
		if player.current_bet == self.to_pay:  # checa se player já cobriu aposta
			self.checked_players = self.checked_players + 1
			response = "Player " + str(self.current_player) + " has checked."
			response_data['result'] = 1
			if self.checked_players == self.active_players:  # acabou rodada de apostas
				self.next_phase()
			else:  # não acabou a rodada de apostas, passa pro proximo player
				self.next_player()
		else:
			response = "Player has not yet covered all bets."
			response_data['result'] = 0

		response_data['log'] = response
		response_data['stack'] = player.stack
		response_data['pot'] = self.pot
		response_data['phase'] = self.phase
		return response_data
		# else:
		# exception > players não pagou a aposta. Na real essa checagem idealmente seria feita a cada começo
		# de turno do player e desativaria o botão Check.

	def next_player(self):
		self.current_player = self.current_player + 1
		if self.current_player == len(self.players):
			self.current_player = 0

	def raise_JSON(self, amount):
		player = self.players[self.current_player]
		response_data = {}
		total = amount + self.to_pay - player.current_bet 
		if player.stack >= total:
			self.pot = self.pot + total
			self.checked_players = 1
			self.to_pay = amount + self.to_pay 
			player.current_bet = self.to_pay
			player.stack = player.stack - total
			self.next_player()
			response_data['result'] = 1
			response_data['log'] = 'Player' + str(self.current_player) + ' has raised to ' + str(player.current_bet)
			response_data['stack'] = player.stack
			response_data['pot'] = self.pot
			response_data['phase'] = self.phase
			return response_data

	def raise_bet(self, amount):
		player = self.players[self.current_player]
		response_data = {}
		total = amount + self.to_pay - player.current_bet 
		if player.stack >= total:
			self.pot = self.pot + total
			self.checked_players = 1
			self.to_pay = amount + self.to_pay 
			player.current_bet = self.to_pay
			player.stack = player.stack - total
			ret = "Player " + str(self.current_player) + "has raised to " + str(self.to_pay)
			self.next_player()
			return ret
		else:
			return "Not enough money"


	def call_JSON(self):

		response_data = {}
		player = self.players[self.current_player]

		if self.to_pay == 0:
			response_data['result'] = 0
			response_data['log'] = 'Player has already covered all bets'
			response_data['stack'] = player.stack
			response_data['pot'] = self.pot
			response_data['phase'] = self.phase
			return response_data

		response = "Player " + str(self.current_player) + " "

		total = self.to_pay - player.current_bet

		if player.stack >= total:
			self.pot = self.pot + total
			player.stack = player.stack - total
			player.current_bet = player.current_bet + self.to_pay
			self.checked_players = self.checked_players + 1

			if self.checked_players == self.active_players:  # acabou rodada de apostas
				self.next_phase()
			else:
				self.next_player()
			response = response + "has called for " + \
				str(total) + " chips."
			
			response_data['result'] = 1
			response_data['log'] = response
			response_data['stack'] = player.stack
			response_data['pot'] = self.pot
			response_data['phase'] = self.phase

			return response_data
		else:
			response = response + "has not enough to cover, so they went all in. NOT IMPLEMENTED YET."
			return response
			#return HttpResponse(json.dumps(response_data), content_type="application/json"

	def call(self):
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
			if self.checked_players == self.active_players:  # acabou rodada de apostas
				self.next_phase()
			else:
				self.next_player()
			response = response + "has called for " + \
				str(self.to_pay) + " chips."
			return response
		else:
			response = response + "has not enough to cover, so they went all in. NOT IMPLEMENTED YET."
			return response

	def fold(self):
		del self.players[self.current_player]
		self.active_players = self.active_players - 1
		if self.active_players == 1:
			# acabou mão, player ganhou
			self.finish_hand()

	def finish_hand(self):
		winner = ""

		if self.active_players > 1:
			self.compute_players()
			score = 0
			board = [Card(self.flop1.power, self.flop1.suit), Card(self.flop2.power, self.flop2.suit) , Card(self.flop3.power, self.flop3.suit), Card(self.turn.power, self.turn.suit), Card(self.river.power, self.river.suit)]
			for player in self.players:

				hole = [Card(player.card1[0].power, player.card1[0].suit), Card(player.card2[0].power, player.card2[0].suit)]
				new_score = HandEvaluator.evaluate_hand(hole, board)
				if new_score > score:
					score = new_score
					winner = player
		else:
			winner = self.players[0]

		winner.stack = winner.stack + self.pot
		self.pot = 0
		self.phase = 0
		self.current_player = 0
		self.active_players = len(self.all_players)
		self.checked_players = 0
		self.to_pay = 0
		self.players = []
		self.deck = build_deck()
		for player in self.all_players:
			player.card1 = [compute_draw_card(self.deck)]
			player.card2 = [compute_draw_card(self.deck)]
		self.flop1 = compute_draw_card(self.deck)
		self.flop2 = compute_draw_card(self.deck)
		self.flop3 = compute_draw_card(self.deck)
		self.players = self.all_players[:]
		# dar o dinheiro pro player vencedor e resetar tudo.

	def measure_players(self):
		for player in self.players:
			for i in range(player.next_qubit1):
				player.circuit.append(cirq.measure(player.qubits[i]))

			for i in range(player.next_qubit2):
				player.circuit.append(cirq.measure(player.qubits[i + 5]))


	def compute_players(self):
		
		self.measure_players()
		simulator = Simulator()
		for player in self.players:
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

		if len(player.card1) > 1:
			player.card1 = [player.card1.pop(int(bits1, 2))]

		if len(player.card2) > 1:
			player.card2 = [player.card2.pop(int(bits2, 2))]


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

		if self.phase == 2:
			self.turn = compute_draw_card(self.deck)
			self.cards.append(self.turn)

		if self.phase == 3:
			self.river = compute_draw_card(self.deck)
			self.cards.append(self.river)


		if self.phase == 4:
			self.finish_hand()


def build_deck():
	numbers = list(range(2, 11))
	numbers.append('J')
	numbers.append('Q')
	numbers.append('K')
	numbers.append('A')
	powers = list(range(2, 15))
	suits = ['♡', '♠', '♣', '♢']
	suits_numbers = [1, 2, 3, 4]

	deck = []
	for i in range(len(numbers))	:
		for j in range(len(suits)):
			card = _Card(str(numbers[i]) + suits[j] +
						 " ", powers[i], suits_numbers[j])
			deck.append(card)

	#deck_id = str(uuid.uuid4())
	cache.set('deck', deck)
	return deck


def view_deck(request):
	return HttpResponse(cache.get('deck'))


def compute_draw_card(deck):
	deck = cache.get('deck', deck)
	position = random.randint(0, len(deck) - 1)
	card = deck.pop(position)
	cache.set('deck', deck)
	return card


def index(request):
	return HttpResponse(build_deck())

def show_table_HTML (request, context={}):
	table = cache.get('table')
	i = 0
	if table.phase >= 1:
		context["flop1"] = table.flop1.name
		context["flop2"] = table.flop2.name
		context["flop3"] = table.flop3.name

	if table.phase >= 2:
		context["turn"] = table.turn.name

	if table.phase == 3:
		context["river"] = table.river.name

	context["active_player"] = str(table.current_player)
	context["pot"] = str(table.pot)
	context["player0_stack"] = str(table.players[0].stack)
	context["player0_card1"] = table.players[0].get_card1()
	context["player0_card2"] = table.players[0].get_card2()

	context["player1_stack"] = str(table.players[1].stack)
	context["player1_card1"] = table.players[1].get_card1()
	context["player1_card2"] = table.players[1].get_card2()
	
	rendered = render_to_string('main.html', context)

	return HttpResponse(rendered)


def show_table (request):
	table = cache.get('table')
	response = ""
	i = 0
	if table.phase >= 1:
		response = response + str(table.flop1.name) + \
			str(table.flop2.name) + str(table.flop3.name)

	if table.phase >= 2:
		response = response + str(table.turn.name)

	if table.phase >= 3:
		response = response + str(table.river.name)

	response = response + " Pot: " + \
		str(table.pot) + " Active player is " + \
		str(table.current_player) + ".\n"

	for player in table.players:
		response = response + " Player " + \
			str(i) + " has " + str(player.stack) + " chips and "
		response = response + "("
		for card in player.card1:
			response = response + card.name
		response = response + ") ("
		for card in player.card2:
			response = response + card.name
		response = response + ")"
		response = response + " as hand." + str(table.phase)
		i = i + 1
	return HttpResponse(response)


def build_hand(request):
	deck = build_deck()

	player1 = Player(compute_draw_card(deck), compute_draw_card(
		deck), cirq.LineQubit.range(10), 1, cirq.Circuit())
	player2 = Player(compute_draw_card(deck), compute_draw_card(
		deck), cirq.LineQubit.range(10), 2, cirq.Circuit())

	table = Table(compute_draw_card(deck), compute_draw_card(
		deck), compute_draw_card(deck), [player1, player2], deck)
	cache.set('table', table)

	#response = str(table.flop1) + str(table.flop2) + str(table.flop3) + str(table.pot)
	return HttpResponse("Hand Start!")

def build_hand_JSON(request):
	deck = build_deck()
	player1 = Player(compute_draw_card(deck), compute_draw_card(deck), cirq.LineQubit.range(10), 1, cirq.Circuit())
	player2 = Player(compute_draw_card(deck), compute_draw_card(deck), cirq.LineQubit.range(10), 2, cirq.Circuit())

	table = Table(compute_draw_card(deck), compute_draw_card(deck), compute_draw_card(deck), [player1, player2], deck)
	cache.set('table', table)
	response_data = {}
	card = {}
	card['rank'] = player1.card1[0].power
	card['suit'] = player1.card1[0].suit
	response_data['P1C1'] = card
	return HttpResponse(json.dumps(response_data), content_type="application/json")


def check(request):
	table = cache.get('table')
	log = table.check()
	context = {}
	context["log"] = log
	cache.set('table', table)
	return show_table_HTML(request, context)

def check_old(request):
	table = cache.get('table')
	response = table.check()
	cache.set('table', table)
	return HttpResponse(response)

def check_JSON(request):
	table = cache.get('table')
	response_data = table.check_JSON()
	cache.set('table', table)
	return HttpResponse(json.dumps(response_data), content_type="application/json")

def call(request):
	table = cache.get('table')
	table.call()
	cache.set('table', table)
	return show_table_HTML(request)

def call_JSON(request):
	table = cache.get('table')
	response_data = table.call_JSON()
	cache.set('table', table)
	return HttpResponse(json.dumps(response_data), content_type="application/json")

def fold(request):
	table = cache.get('table')
	response_data = table.fold()
	cache.set('table', table)
	return show_table_HTML(request)

@csrf_exempt 
def raise_bet (request):
	table = cache.get('table')
	amount = int(request.POST.get('bet'))
	log = table.raise_bet(amount)
	context = {}
	context["log"] = log
	cache.set('table', table)
	return show_table_HTML(request, context)

def raise_JSON(request, amount=100):
	table = cache.get('table')
	response_data = table.raise_JSON(amount)
	cache.set('table', table)
	return HttpResponse(json.dumps(response_data), content_type="application/json")



def draw_card (request):
	#template = loader.get_template('main.html')
	rendered = render_to_string('main.html', {'current_player': 'Player1', 'stack':10000})

	#return render(request,'main.html')
	return HttpResponse(rendered)


def quantum_draw(request):
	# Caso o card esteja normal, transforma em qubit
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
		new_card = compute_draw_card(deck)
		new_card.binary_position = to_bin((len(card) + i), next_qubit + 1)
		new_cards.append(new_card)

	card = card + new_cards

	if offset == 0:
		player.next_qubit1 = player.next_qubit1 + 1
	else:
		player.next_qubit2 = player.next_qubit2 + 1

	player.card1 = card
	cache.set('table', table)

	context = {}
	context["log"] = "Player " + str(table.current_player) + " has quantum drawed."
	return show_table_HTML(request, context)


def resolve_player(player, bits1, bits2):
	if len(player.card1) > 1:
		player.card1 = [player.card1.pop(int(bits1, 2))]

	if len(player.card2) > 1:
		player.card2 = [player.card2.pop(int(bits2, 2))]


def calculate_hand(request):

	table = cache.get('table')
	player = table.players[0]
	board = []
	for card in table.cards:
		board.append(Card(card.power, card.suit))
	
	hole = [Card(player.card1[0].power, player.card1[0].suit),
			Card(player.card2[0].power, player.card2[0].suit)]

	score = HandEvaluator.evaluate_hand(hole, board)

	return HttpResponse(str(score))


def compare_cards(card1, card2):
	return card1.power < card2.power

def test(response):

	deck = build_deck()
	board = []
	hole = []
	hole2 = []
	response = ""
	for i in range(5):
		card = compute_draw_card(deck)
		board.append(Card(card.power, card.suit))
		response = response + " " + card.name
	
	response = response + "-------- P1 "
	for i in range(2):
		card = compute_draw_card(deck)
		hole.append(Card(card.power, card.suit))
		response = response + " " + card.name
	response = response + "-------- P2 "

	for i in range(2):
		card = compute_draw_card(deck)
		hole2.append(Card(card.power, card.suit))
		response = response + " " + card.name
	
	response = response + "------------ Score "

	score = HandEvaluator.evaluate_hand(hole, board)
	score2 = HandEvaluator.evaluate_hand(hole2, board)
	return HttpResponse(response + "" + str(score) + " " + str(score2))

def to_bin(x, n=0):
	return format(x, 'b').zfill(n)
