import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine


Base = declarative_base()



class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, primary_key = True)
	name = Column(String(250), nullable = False)
	email = Column(String(250), nullable = False)
	photo = Column(String(350), nullable = True)


class Category(Base):
	__tablename__ = 'category'
	id = Column(Integer, primary_key = True)
	title = Column(String(30), nullable = False)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User, backref='category')

	@property
	def serialize(self):
		return{
			'id' : self.id,
			'title' : self.title,
			'user_id' : self.user_id
		}




class Item(Base):
	__tablename__ = 'item'
	id = Column(Integer, primary_key = True)
	title = Column(String(30), nullable = False)
	description = Column(String(400), nullable = True)
	photo = Column(String(350), nullable = True)
	price = Column(String(20), nullable = True)
	category_id = Column(Integer, ForeignKey('category.id'))
	category = relationship(Category, backref='item')
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User, backref='item')

	@property
	def serialize(self):
		return{
			'title' : self.title,
			'description' : self.description,
			'id' : self.id,
			'photo' : self.photo,
			'category' : self.category.title,
			'user_id' : self.user_id
		}




engine = create_engine('sqlite:///seederwithusers.db')

# engine = create_engine('sqlite:///catalogTestWithUsers.db')

# engine = create_engine('sqlite:///catalogTest.db')

# engine = create_engine('sqlite:///catalog.db')


Base.metadata.create_all(engine)