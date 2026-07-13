import sqlite3

from Extensions.theme_store import DARK_THEME, DEFAULT_THEME, LIGHT_THEME, ThemeStore


def _connection_with_row(theme=DEFAULT_THEME):
    connection = sqlite3.connect(":memory:")
    connection.execute('CREATE TABLE Color ("Primary" TEXT, "Foreground" TEXT, "Gray" TEXT)')
    connection.execute("INSERT INTO Color VALUES (?, ?, ?)", theme.as_tuple())
    connection.commit()
    return connection


def test_load_returns_the_stored_theme():
    theme = ThemeStore(_connection_with_row()).load()
    assert theme == DEFAULT_THEME


def test_load_returns_default_when_table_is_empty():
    connection = sqlite3.connect(":memory:")
    connection.execute('CREATE TABLE Color ("Primary" TEXT, "Foreground" TEXT, "Gray" TEXT)')
    assert ThemeStore(connection).load() == DEFAULT_THEME


def test_set_mode_light_persists_and_reloads():
    store = ThemeStore(_connection_with_row())
    theme = store.set_mode("light")
    assert theme == LIGHT_THEME
    assert store.load() == LIGHT_THEME


def test_set_mode_defaults_to_dark_for_unknown_value():
    store = ThemeStore(_connection_with_row())
    assert store.set_mode("something-else") == DARK_THEME


def test_construction_creates_missing_table_and_load_falls_back_to_default():
    # Simulates a fresh/packaged build's blank Data.db, which has no Color
    # table at all yet - load() should self-heal instead of raising.
    connection = sqlite3.connect(":memory:")
    store = ThemeStore(connection)
    assert store.load() == DEFAULT_THEME


def test_save_inserts_when_table_starts_empty():
    connection = sqlite3.connect(":memory:")
    store = ThemeStore(connection)
    store.save(LIGHT_THEME)
    assert store.load() == LIGHT_THEME
