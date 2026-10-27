"""Delivery region persists locally, never in source control or public fixtures."""
import re


def postal_code(value):
    value = value.strip().replace('-', '')
    if not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError('Informe oito números: /cep 01001000.')
    return value


def load_profile(db, config):
    rows = db.rows("SELECT value FROM preferences WHERE key='grocery_postal_code'")
    if rows:
        config.grocery_postal_code = postal_code(rows[0]['value'])


def save_profile(db, config, value):
    value = postal_code(value)
    db.run("INSERT INTO preferences(key,value) VALUES ('grocery_postal_code',?) "
           "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (value,))
    config.grocery_postal_code = value
    return value[:5] + '-' + value[5:]
