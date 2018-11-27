# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import factory
import factory.fuzzy
from django.conf import settings
from django.utils import timezone

from .models import Comment, Ticket


class UserFactory(factory.django.DjangoModelFactory):

    username = factory.fuzzy.FuzzyText(length=12)
    email = factory.LazyAttribute(lambda o: '%s@example.org' % o.username)
    last_login = factory.LazyFunction(timezone.now)
    is_active = True

    class Meta:
        model = settings.AUTH_USER_MODEL


class TicketFactory(factory.django.DjangoModelFactory):

    title = factory.fuzzy.FuzzyText(length=64)
    body = factory.fuzzy.FuzzyText(length=64)
    author = factory.SubFactory(UserFactory)

    class Meta:
        model = Ticket


class CommentFactory(factory.django.DjangoModelFactory):

    body = factory.fuzzy.FuzzyText(length=64)
    author = factory.SubFactory(UserFactory)
    ticket = factory.SubFactory(TicketFactory)

    class Meta:
        model = Comment
