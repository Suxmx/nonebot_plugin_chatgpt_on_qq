class OverMaxTokenLengthError(Exception):
    def __init__(self,ErrorInfo):
        self.ErrorInfo=ErrorInfo
    def __str__(self) -> str:
        return self.ErrorInfo
class NoResponseError(Exception):
    def __init__(self,ErrorInfo):
        self.ErrorInfo=ErrorInfo
    def __str__(self) -> str:
        return self.ErrorInfo