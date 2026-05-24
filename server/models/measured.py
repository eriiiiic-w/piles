from sqlalchemy import Column, Integer, String, Float
from server.database import Base


class Measured(Base):
    __tablename__ = "measured"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pile_no = Column(String, nullable=False, index=True)
    layer_name = Column(String, nullable=False)
    measured_elev = Column(Float, nullable=False)
    actual_depth = Column(Float, nullable=True)
    recorded_at = Column(String)
