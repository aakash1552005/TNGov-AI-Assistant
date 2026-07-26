"""ORM models package.

Import all models here so that ``Base.metadata`` is fully populated
when ``create_all`` is called in ``main.py``.
"""

from app.models.chat import ChatHistory  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.scheme import Scheme  # noqa: F401
from app.models.user import User  # noqa: F401
