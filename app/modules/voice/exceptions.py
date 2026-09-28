class VoiceError(Exception):
    pass


class VoiceNotConfiguredError(VoiceError):
    pass


class VoiceFileTooLargeError(VoiceError):
    pass


class VoiceProviderError(VoiceError):
    pass
