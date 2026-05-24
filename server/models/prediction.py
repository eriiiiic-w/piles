from sqlalchemy import Column, Integer, String, Float
from server.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pile_no = Column(String, nullable=False, index=True)
    layer_name = Column(String, nullable=False)
    top_elev_pred = Column(Float)
    bottom_elev_pred = Column(Float)
    method = Column(String, default="克里金法")
    created_at = Column(String)
