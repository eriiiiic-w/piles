from sqlalchemy import Column, Integer, String, Float
from server.database import Base


class SoilParam(Base):
    __tablename__ = "soil_params"
    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_name = Column(String, unique=True, nullable=False)
    qsik = Column(Float, default=0.0)
    qpk = Column(Float, default=0.0)
