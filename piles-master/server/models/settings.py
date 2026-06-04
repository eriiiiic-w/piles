from sqlalchemy import Column, String
from server.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, default="")
