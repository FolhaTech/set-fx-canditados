class AutomationError(Exception):
    pass


# Triata
class TriataError(AutomationError):
    pass


class TriataLoginError(TriataError):
    pass


class TarefaNotFoundError(TriataError):
    pass


class FormExtractionError(TriataError):
    pass


# Data
class JsonNotFoundError(AutomationError):
    pass


class MandatoryFieldError(AutomationError):
    pass


# PDF
class PDFError(AutomationError):
    pass


class PDFGenerationError(PDFError):
    pass


class PDFNotFoundError(PDFError):
    pass


class TemplateNotFoundError(PDFError):
    pass


# ZapSign
class ZapSignError(AutomationError):
    pass


class ZapSignLoginError(ZapSignError):
    pass


class ZapSignUploadError(ZapSignError):
    pass


class ZapSignLinkError(ZapSignError):
    pass


# Browser
class BrowserError(AutomationError):
    pass


class ElementNotFoundError(BrowserError):
    pass


class ClickFailedError(BrowserError):
    pass
