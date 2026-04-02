from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

# для тестов в оперативной памяти
# DATABASE_URL = "sqlite:///:memory:"

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
