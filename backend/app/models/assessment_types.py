from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import Record


class AssessmentType(Record, Base):
    __tablename__ = "assessment_types"
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    purpose: Mapped[str] = mapped_column(String(500))
