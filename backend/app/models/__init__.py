"""ORM models — import all so Alembic/create_tables sees them."""

from app.models.site import Site          # noqa: F401
from app.models.analysis import AnalysisResult  # noqa: F401
from app.models.photo import Photo        # noqa: F401
from app.models.user import User          # noqa: F401
