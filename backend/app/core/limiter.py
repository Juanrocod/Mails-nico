from slowapi import Limiter
from slowapi.util import get_remote_address

# The RATELIMIT_ENABLED environment variable is read by slowapi's Limiter at __init__
# conftest.py sets RATELIMIT_ENABLED=false before importing app.main
# Note: slowapi reads from os.environ when the enabled parameter is not passed (default=True),
# and properly casts using the cast parameter. If we pass enabled=False, slowapi's get_app_config
# skips the cast due to False being falsy, causing the string "false" to be treated as truthy.

limiter = Limiter(key_func=get_remote_address)
