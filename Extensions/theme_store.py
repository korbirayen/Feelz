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
        # Self-healing: a fresh/packaged build's Data.db won't have this
        # table yet (only the repo's checked-in seed copy does), and without
        # it load()/save() would hit "no such table: Color" instead of
        # falling back to DEFAULT_THEME.
        self.connection.execute(
            'CREATE TABLE IF NOT EXISTS Color ("Primary" TEXT, "Foreground" TEXT, "Gray" TEXT)'
        )
        self.connection.commit()

    def load(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT "Primary", "Foreground", "Gray" FROM Color LIMIT 1')
        row = cursor.fetchone()
        if not row:
            return DEFAULT_THEME
        return Theme(*row)

    def save(self, theme):
        cursor = self.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM Color')
        (count,) = cursor.fetchone()
        if count:
            cursor.execute(
                'UPDATE Color SET "Primary" = ?, "Foreground" = ?, "Gray" = ?',
                theme.as_tuple(),
            )
        else:
            # No seed row (fresh/packaged build) - insert instead of a no-op UPDATE.
            cursor.execute(
                'INSERT INTO Color ("Primary", "Foreground", "Gray") VALUES (?, ?, ?)',
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
