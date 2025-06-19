from django.db import models
from django.contrib.auth.models import User

class Venue(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name

class Wrestler(models.Model):
    name = models.CharField(max_length=255)
    real_name = models.CharField(max_length=255, blank=True, null=True)
    aliases = models.CharField(max_length=255, blank=True, null=True)
    debut_year = models.IntegerField(blank=True, null=True)
    hometown = models.CharField(max_length=255, blank=True, null=True)
    nationality = models.CharField(max_length=255, blank=True, null=True)
    finishers = models.TextField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Promotion(models.Model):
    name = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=50, blank=True, null=True)
    nicknames = models.CharField(max_length=255, blank=True, null=True)
    founded_year = models.IntegerField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    name = models.CharField(max_length=255)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateTimeField()
    attendance = models.IntegerField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Title(models.Model):
    name = models.CharField(max_length=255)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    debut_year = models.IntegerField(blank=True, null=True)
    retirement_year = models.IntegerField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Match(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    wrestler1 = models.ForeignKey(Wrestler, on_delete=models.CASCADE, related_name='match_wrestler1')
    wrestler2 = models.ForeignKey(Wrestler, on_delete=models.CASCADE, related_name='match_wrestler2')
    match_text = models.TextField()
    result = models.CharField(max_length=255, blank=True, null=True)
    match_type = models.CharField(max_length=255, blank=True, null=True)
    title = models.ForeignKey(Title, on_delete=models.SET_NULL, blank=True, null=True)
    about = models.TextField(blank=True, null=True)

class VideoGame(models.Model):
    name = models.CharField(max_length=255)
    promotions = models.CharField(max_length=255, blank=True, null=True)
    release_year = models.IntegerField(blank=True, null=True)
    systems = models.CharField(max_length=255, blank=True, null=True)
    about = models.TextField(blank=True, null=True)

class Podcast(models.Model):
    name = models.CharField(max_length=255)
    hosts = models.CharField(max_length=255, blank=True, null=True)
    related_wrestlers = models.CharField(max_length=255, blank=True, null=True)
    launch_year = models.IntegerField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    about = models.TextField(blank=True, null=True)

class Special(models.Model):
    title = models.CharField(max_length=255)
    release_year = models.IntegerField(blank=True, null=True)
    related_wrestlers = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    about = models.TextField(blank=True, null=True)

class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=64)
    is_paid = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    last_reset = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

