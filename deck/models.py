from django.db import models

# Create your models here.


class Card(models.Model):
    name = models.CharField(max_length=3)
    binary_position = models.CharField(max_length=5)

# O Model precisa ter só o que front end lê?

		