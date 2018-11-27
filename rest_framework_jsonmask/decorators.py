from __future__ import unicode_literals

from functools import wraps


def data_predicate(*field_names):
    def _data_predicate(fnc):
        fnc._data_function_predicates = field_names

        @wraps(fnc)
        def inner(self, queryset):
            return fnc(self, queryset)

        return inner

    return _data_predicate
