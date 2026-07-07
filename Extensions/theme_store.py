from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    primary: str
    foreground: str
    gray: str

    def as_tuple(self):
        return self.primary, self.foreground, self.gray


DEFAULT_THEME = Theme("#181818", "#ffffff", "#3d3d3d")
LIGHT_THEME = Theme("#ffffff", "#222222", "#e0e0e0")
DARK_THEME = DEFAULT_THEME


class ThemeStore:
    def __init__(self, connection):
        self.connection = connection

    def load(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT "Primary", "Foreground", "Gray" FROM Color LIMIT 1')
        row = cursor.fetchone()
        if not row:
            return DEFAULT_THEME
        return Theme(*row)

    def save(self, theme):
        cursor = self.connection.cursor()
        cursor.execute(
            'UPDATE Color SET "Primary" = ?, "Foreground" = ?, "Gray" = ?',
            theme.as_tuple(),
        )
        self.connection.commit()

    def set_mode(self, mode):
        normalized = (mode or "").strip().lower()
        if normalized == "light":
            theme = LIGHT_THEME
        else:
            theme = DARK_THEME
        self.save(theme)
        return theme
