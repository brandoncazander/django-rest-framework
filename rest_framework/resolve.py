"""
Provide reverse functions that return fully qualified URLs
"""
from __future__ import unicode_literals
from django.core.urlresolvers import resolve as django_resolve


def resolve(path, urlconf=None, request=None):
    """
    If versioning is being used then we pass any `resolve` calls through
    to the versioning scheme instance, so that the resulting view name
    can be modified if needed.
    """
    scheme = getattr(request, 'versioning_scheme', None)
    if scheme is not None:
        return scheme.resolve(path, urlconf, request)
    return django_resolve(path, urlconf)
