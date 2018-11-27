from __future__ import unicode_literals

from django.conf import settings
from django.utils import six
from django.utils.functional import cached_property
from jsonmask import parse_fields, should_include_variable
from rest_framework import exceptions

from . import constants
from .utils import collapse_includes_excludes


class OptimizedQuerySetBase(type):
    def __new__(cls, name, bases, attrs):
        new_cls = super(OptimizedQuerySetBase, cls).__new__(cls, name, bases, attrs)
        new_cls._data_predicates = new_cls.extract_data_predicates(attrs)
        return new_cls

    def extract_data_predicates(cls, attrs):
        data_predicates = {}
        for key, value in attrs.items():
            if hasattr(value, '_data_function_predicates'):
                for data_function_predicate in value._data_function_predicates:
                    data_predicates[data_function_predicate] = value
        return data_predicates


@six.add_metaclass(OptimizedQuerySetBase)
class OptimizedQuerySetMixin(object):
    """
    Allows a Google Partial Response query param like to prune results
    """

    def get_serializer_context(self):
        context = super(OptimizedQuerySetMixin, self).get_serializer_context()

        fields_name = getattr(settings, 'REST_FRAMEWORK_JSONMASK_FIELDS_NAME', constants.FIELDS_NAME)
        excludes_name = getattr(settings, 'REST_FRAMEWORK_JSONMASK_EXCLUDES_NAME', constants.EXCLUDES_NAME)

        if fields_name in self.request.GET and excludes_name in self.request.GET:
            raise exceptions.ParseError(
                detail='Cannot provide both "%s" and "%s"' % (fields_name, excludes_name,)
            )

        if fields_name in self.request.GET:
            context['requested_fields'] = self.requested_fields
        elif excludes_name in self.request.GET:
            context['excluded_fields'] = self.excluded_fields

        return context

    @cached_property
    def requested_fields(self):
        fields_name = getattr(settings, 'REST_FRAMEWORK_JSONMASK_FIELDS_NAME', constants.FIELDS_NAME)
        return parse_fields(self.request.GET.get(fields_name))

    @cached_property
    def excluded_fields(self):
        excludes_name = getattr(settings, 'REST_FRAMEWORK_JSONMASK_EXCLUDES_NAME', constants.EXCLUDES_NAME)
        return parse_fields(self.request.GET.get(excludes_name))

    def optimize_queryset(self, queryset):
        if self.requested_fields and self.excluded_fields:
            raise exceptions.ParseError('Cannot provide both `fields` and `excludes`')

        if self.requested_fields or self.excluded_fields:
            return self.apply_requested_data_functions(
                queryset, self.requested_fields, self.excluded_fields
            )
        return self.apply_all_data_functions(queryset)

    def apply_requested_data_functions(self, queryset, fields, excludes):
        requested_structure, is_negated = collapse_includes_excludes(fields, excludes)
        for dotted_path, data_function in self._data_predicates.items():
            if should_include_variable(
                dotted_path, requested_structure, is_negated=is_negated
            ):
                queryset = data_function(self, queryset)
        return queryset

    def apply_all_data_functions(self, queryset):
        for _, data_function in self._data_predicates.items():
            queryset = data_function(self, queryset)
        return queryset

    def get_queryset(self):
        queryset = super(OptimizedQuerySetMixin, self).get_queryset()
        return self.optimize_queryset(queryset)
