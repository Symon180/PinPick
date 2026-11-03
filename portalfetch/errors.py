"""Errori del dominio, con un codice di uscita per ognuno (utile a scheduler e CI)."""

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_CONFIG = 2


class PortalError(Exception):
    """Base di tutti gli errori previsti dal motore."""


class ConfigError(PortalError):
    """Configurazione mancante o non valida."""


class AuthenticationRequired(PortalError):
    """Credenziali rifiutate. Il motore NON riprova: un account si puo bloccare."""


class PortalUnavailable(PortalError):
    """Sito non raggiungibile o pagina diversa dal previsto (layout cambiato)."""
