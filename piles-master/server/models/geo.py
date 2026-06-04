from sqlalchemy import Column, Integer, String, Float
from server.database import Base


class GeoLayer(Base):
    __tablename__ = "geo_layers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hole_id = Column(String, nullable=False, index=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    layer_name = Column(String, nullable=False)
    top_elev = Column(Float, nullable=False)
    thickness = Column(Float, default=2.0)
    bottom_elev = Column(Float, nullable=True)
