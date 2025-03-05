class CustomTimeoutError(TimeoutError):
    """
    Custom exception to handle timeout errors in bot operations.

    Default message: "Timeout reached, please try again."
    """

    def __init__(self, message="Timeout reached, please try again."):
        super().__init__(message)


class EmptyMessageError(ValueError):
    """
    Custom exception for handling empty message errors.

    Default message: "Empty message. Please send a valid message."
    """

    def __init__(self, message="Empty message. Please send a valid message."):
        super().__init__(message)
