"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

Reads are always capped, so one request can never pull a whole history.
"""
from rest_framework.pagination import LimitOffsetPagination


class CappedLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200
