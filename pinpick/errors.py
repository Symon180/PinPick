"""Errori del dominio, con codici di uscita."""

EXIT_OK = 0
EXIT_NO_RESULTS = 1
EXIT_CONFIG = 2
EXIT_API = 3


class PinPickError(Exception):
    exit_code = EXIT_API


class ConfigError(PinPickError):
    """Token mancante o parametri non validi."""

    exit_code = EXIT_CONFIG


class AuthError(PinPickError):
    """Token rifiutato o scaduto (HTTP 401/403)."""

    exit_code = EXIT_CONFIG


class ApiError(PinPickError):
    """Pinterest non risponde, limite di richieste superato o risposta inattesa."""
