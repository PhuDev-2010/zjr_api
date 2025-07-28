class ZaloAPIException(Exception):
    """Custom exception thrown by ``zjr_api``.

    All exceptions in the ``zjr_api`` module inherits this.
    """

class LoginMethodNotSupport(ZaloAPIException):
	"""Raised by zjr_api if:

    - Using an unsupported login method.
    """
	def __init__(self, message=None):
		self.message = message
		super().__init__(message)
		

class ZaloLoginError(ZaloAPIException):
	def __init__(self, message=None):
		self.message = message
		super().__init__(message)
		

class ZaloUserError(ZaloAPIException):
	"""Thrown by ``zjr_api`` when wrong values are entered."""
	def __init__(self, message=None):
		self.message = message
		super().__init__(message)


class EncodePayloadError(ZaloAPIException):
	"""Raised by ``zjr_api`` if:

    - The secret key is not correct to encode the payload
    - Payload data does not match.
    - A conflict occurred when encoding the payload.
    """
	def __init__(self, message=None):
		self.message = message
		super().__init__(message)
		
		
class DecodePayloadError(ZaloAPIException):
	"""Raised by ``zjr_api`` if:

    - The secret key is not correct to decode the payload
    - Payload data does not match.
    - A conflict occurred when decoding the payload.
    """
	def __init__(self, message=None):
		self.message = message
		super().__init__(message)
		
