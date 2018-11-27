from __future__ import unicode_literals

from django.conf import settings
from jsonmask import apply_json_mask, parse_fields

from . import constants


def extract_json_mask_from_request(request):
    includes, excludes = {}, {}

    excludes_name = getattr(settings, 'REST_FRAMEWORK_JSONMASK_EXCLUDES_NAME', constants.EXCLUDES_NAME)
    fields_name = getattr(settings, 'REST_FRAMEWORK_JSONMASK_FIELDS_NAME', constants.FIELDS_NAME)

    if fields_name in request.GET:
        includes = parse_fields(request.GET[fields_name])
    if excludes_name in request.GET:
        excludes = parse_fields(request.GET[excludes_name])

    if includes and excludes:
        raise ValueError('Cannot supply both `%s` and `%s`' % (fields_name, excludes_name,))

    return includes, excludes


def apply_json_mask_from_request(data, request):
    includes, excludes = extract_json_mask_from_request(request)
    json_mask, is_negated = collapse_includes_excludes(includes, excludes)
    return apply_json_mask(data, json_mask, is_negated)


def collapse_includes_excludes(includes, excludes):
    """
    :includes:  dict    Possible parsed `?fields=` data
    :excludes:  dict    Possible parsed `?excludes=` data

    :returns:   tuple   (dict, bool,)
                        Where dict is includes or excludes, whichever
                        was Truthy, and bool is `is_negated` -- aka,
                        True if `excludes` was the Truthy val
    """
    if includes:
        return includes, False
    return excludes, True
