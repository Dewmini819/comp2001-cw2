from sqlalchemy import Column, Integer, String
from database import Base

class Profile(Base):
    __tablename__ = "profiles"

    profile_id = Column(Integer, primary_key=True, index=True)
    auth_email = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    location = Column(String, nullable=True)
    role = Column(String, nullable=False, default="User")
