"""Owner: Kenneth Master (System architect)

Reads are always capped, so one request can never pull a whole history.
"""
from rest_framework.pagination import LimitOffsetPagination


class CappedLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200
