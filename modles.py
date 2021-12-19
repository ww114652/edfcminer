from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, select
from sqlalchemy.orm import registry, relationship, Session

DB_PATH = "edfc.db"
# engine = create_engine("sqlite+pysqlite:///:memory:", echo=True, future=True)
engine = create_engine(f"sqlite+pysqlite:///{DB_PATH}", echo=True, future=True)

mapper_registry = registry()
Base = mapper_registry.generate_base()
class TPost(Base):
    __tablename__ = "post"

    idx = Column(Integer, primary_key=True)
    str = Column(String)
    tid = Column(Integer, ForeignKey("thread.id"), primary_key=True,)

    def __repr__(self):
        return f"Post(tid={self.tid!r}, idx={self.idx!r}, str={self.str!r})"

class TThread(Base):
    __tablename__ = 'thread'

    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    forum = Column(String(20))
    forum_type = Column(String(1))
    author = Column(String(20))
    ver = Column(Integer, default=0)

    posts = relationship("TPost", order_by=TPost.idx)

    def __repr__(self):
        return f"Thread(id={self.id!r}, title={self.title!r}, forum={self.forum!r}, author={self.author!r}), posts:{len(self.posts)}"

Base.metadata.create_all(engine)