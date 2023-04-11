class MS2PIPError(Exception):
    pass


class InvalidPeptideError(MS2PIPError):
    pass


class InvalidInputError(MS2PIPError):
    pass


class UnknownModificationError(ValueError):
    pass


class InvalidPEPRECError(Exception):
    pass


class NoValidPeptideSequencesError(Exception):
    pass


class UnknownOutputFormatError(ValueError):
    pass


class UnknownModelError(ValueError):
    pass


class MissingConfigurationError(Exception):
    pass


class FragmentationModelRequiredError(Exception):
    pass


class InvalidModificationFormattingError(Exception):
    pass


class InvalidAminoAcidError(Exception):
    pass


class UnsupportedSpectrumFiletypeError(Exception):
    pass


class InvalidSpectrumError(Exception):
    pass


class NoMatchingSpectraFound(MS2PIPError):
    pass


class TitlePatternError(MS2PIPError):
    pass


class InvalidXGBoostModelError(MS2PIPError):
    """XGBoost model file could not be read."""
