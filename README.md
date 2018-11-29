[![Build Status](https://api.travis-ci.com/zapier/django-rest-framework-jsonmask.svg?branch=master)](https://travis-ci.org/zapier/django-rest-framework-jsonmask) [![Coverage Status](https://img.shields.io/coveralls/zapier/django-rest-framework-jsonmask/master.svg)](https://coveralls.io/r/zapier/django-rest-framework-jsonmask) [![PyPI Version](https://img.shields.io/pypi/v/djangorestframework-jsonmask.svg)](https://pypi.org/project/django-rest-framework-jsonmask)

---

## Overview

Implements Google's Partial Response in Django RestFramework

## Requirements

* Python (2.7, 3.6, 3.7)
* Django (1.11, 2.0, 2.1)

## Installation

Install using `pip`...

```bash
$ pip install djangorestframework-jsonmask
```

## Example

Most DRF addons that support `?fields=`-style data pruning do so purely at the serializaton layer. Many hydrate full ORM objects, including all of their verbose relationships, and then cut unwanted data immediately before JSON serialization. Any unwanted related data is still fetched from the database and hydrated into Django ORM objects, which severely undermines the usefulness of field pruning.

`rest_framework_jsonmask` aims to do one better by allowing developers to declaratively augment their queryset in direct relation to individual requests. Under this pattern, you only declare the base queryset and any universal relationships on your ViewSet.queryset, leaving all additional enhancements as runtime opt-ins.

To use `rest_framework_jsonmask`, first include its ViewSet and Serializer mixins in your code where appropriate. The following examples are taken from the mini-project used in this library's own unit tests.

```py
# api/views.py
from rest_framework_jsonmask.views import OptimizedQuerySetMixin

class TicketViewSet(OptimizedQuerySetMixin, viewsets.ReadOnlyModelViewSet):

    # Normally, for optimal performance, you would apply the `select_related('author')`
    # call to the base queryset, but that is no longer desireable for data relationships
    # that your frontend may stop asking for.
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    # Data-predicate declaration is optional, but encouraged. This
    # is where the library really shines!
    @data_predicate('author')
    def load_author(self, queryset):
        return queryset.select_related('author')


# api/serializers.py
from rest_framework_jsonmask.serializers import FieldsListSerializerMixin

class TicketSerializer(FieldsListSerializerMixin, serializers.ModelSerializer):
    # Aside from the mixin, everything else is exactly like normal

    author = UserSerializer()

    class Meta:
        models = my_module.models.Ticket
        fields = ('id', 'title', 'body', 'author',)
```

You have now set up your API to skip unnecessary joins (and possibly prefetches), unless the requesting client requires that data. Let's consider a few hypothetical requests and the responses they will each receive. (For brevity, in each of these examples, I will pretend pagination is turned off.)

```http
GET /api/tickets/

200 OK
[
    {
        "id": 1,
        "title": "This is a ticket",
        "body": "This is its text",
        "author": {
            "id": 5,
            "username": "HomerSimpson",
        }
    }
]
```

Because no `?fields` querystring parameter was provided, author records were still loaded and serialized like normal.

> Note: `rest_framework_jsonmask` treats all requests that lack any field definition as if all possible data is requested, and thus executes all data predicates. In the above example, `author` data was loaded via `selected_related('author')`, and _not_ N+1 queries.

---

```http
GET /api/tickets/?fields=id,title,body

200 OK
[
    {
        "id": 1,
        "title": "This is a ticket",
        "body": "This is its text"
    }
]
```

In this example, since `author` was not specified, it was not only not returned in the response payload - it was never queried for or serialized in the first place.

---

```http
GET /api/tickets/?fields=id,title,body,author/username

200 OK
[
    {
        "id": 1,
        "title": "This is a ticket",
        "body": "This is its text",
        "author": {
            "username": "HomerSimpson",
        }
    }
]
```

In this example, `author` data was loaded via the `?fields` declaration, but no unwanted keys will appear in the response.


#### Nested Relationships

This is all good and fun, but what if `author` has rarely used but expensive relationships, too? `rest_framework_jsonmask` supports this, via the exact same mechanisms spelled out above, though sometimes a little extra attention to detail can be important. Let's now imagine that `AuthorSerializer` looks like this:

```py
class AuthorSerializer(FieldsListSerializerMixin, serializers.ModelSerializer):

    accounts = AccountSerializer(many=True)

    class Meta:
        model = settings.AUTH_USER_MODEL
        fields = ('id', 'username', 'email', 'photo', 'accounts', ...)
```

Naturally, if `accounts` is sensitive, internal data, you simply might not use _this_ serializer for external API consumption. Of course, that would solve your problem about how to decide whether to serialize `accounts` data -- the supplied serializer would know nothing about that field! But, let's pretend that in our case, `accounts` is safe for public consumption, and _some_ ticketing API calls require it for triaging purposes, whereas others do not. In such a situation, we'll redefine our ViewSet like so:

```py
class TicketViewSet(OptimizedQuerySetMixin, viewsets.ReadOnlyModelViewSet):

    # Normally, for optimal performance, you would apply the `select_related('author')`
    # call to the base queryset, but that is no longer desireable for data relationships
    # that your frontend may stop asking for.
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    # Data-predicate declaration is optional, but encouraged. This
    # is where the library really shines!
    @data_predicate('author')
    def load_author(self, queryset):
        return queryset.select_related('author')

    @data_predicate('author.accounts')
    def load_author_with_accounts(self, queryset):
        return queryset.select_related('author').prefetch_related('author__accounts')
```

Now, it is up to the client to decide which of the following options (or anything else imaginable) is most appropriate:

```http
 # Includes specified local fields plus all author fields and relationships

GET /api/tickets/?fields=id,title,author

200 OK
[
    {
        "id": 1,
        "title": "This is a ticket",
        "author": {
            "id": 5,
            "username": "HomerSimpson",
            "accounts": [
                {"all_fields": "will_be_present"}
            ]
        }
    }
]
```

 or


 ```http
 # Includes specified local fields plus specified author fields and relationships

GET /api/tickets/?fields=id,title,author(username,photo)

200 OK
[
    {
        "id": 1,
        "title": "This is a ticket",
        "author": {
            "username": "HomerSimpson",
            "photo": "image_url"
        }
    }
]
 ```

 or

 ```http
# Includes specified local fields plus specified author fields and relationships plus specified accounts fields and relationships

GET /api/tickets/?fields=id,title,author(id,accounts(id,type_of,date))

200 OK
 [
    {
        "id": 1,
        "title": "This is a ticket",
        "author": {
            "id": 5,
            "accounts": [
                {
                    "id": 8001,
                    "type_of": "business",
                    "date": 2018-01-01T12:00:00Z"
                },
                {
                    "id": 6500,
                    "type_of": "trial",
                    "date": 2017-06-01T12:00:00Z"
                }
            ]
        }
    }
]
 ```

In short, know that as long as the entire chain of Serializers implements the `FieldsListSerializerMixin`, arbitrarily deep nesting of `?fields` declarations will be honored. However, in practice, because relationships are expensive to hydrate, you will probably want to limit that information and control what data you actually load using the `@data_predicate` decorator on ViewSet methods.


## Testing

```bash
$ make tests
```

or keep them running on change:

```bash
$ make watch
```

You can also use the excellent [tox](http://tox.readthedocs.org/en/latest/) testing tool to run the tests against all supported versions of Python and Django. Install tox globally, and then simply run:

```bash
$ tox
```

## Documentation

```bash
$ make docs
```
