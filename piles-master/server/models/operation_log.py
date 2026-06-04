from sqlalchemy import Column, Integer, String
from server.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, nullable=False)
    detail = Column(String)
    created_at = Column(String)
