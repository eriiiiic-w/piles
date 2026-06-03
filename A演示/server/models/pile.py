from sqlalchemy import Column, Integer, String, Float
from server.database import Base


class Pile(Base):
    __tablename__ = "piles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pile_no = Column(String, unique=True, nullable=False, index=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    diameter = Column(Float, nullable=False)
    pile_type = Column(String, default="未知")
