"""Identifier range shared by every layer.

Ids are 32-bit signed integers in the database (PostgreSQL INTEGER), so anything outside
1..MAX_ID can never exist. Rejecting it at the edge turns would-be 500s into 422s.
"""

MIN_ID = 1
MAX_ID = 2_147_483_647
