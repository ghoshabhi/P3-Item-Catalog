from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem,User

app = Flask(__name__)

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def test_function(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    
    print "Rest Name :",restaurant.name
    print "creator :",creator.name
    
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    for item in items:
        print "Item Name :",item.name
        print "\n"

def allUsers():
    users = session.query(User).order_by(User.id).all()
    for u in users:
        print "ID :", u.id
        print "Name :", u.name
        print "\n"

def allRestaurants():
    restaurants = session.query(Restaurant).order_by(Restaurant.id).all()
    for r in restaurants:
        print "Rest Name :",r.name
        print "User ID :", r.user_id
        print "User Name :", r.user.name
        print "\n"

def testMenuItems(restaurant_id):
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    for i in items:
        print "Item Name :",i.name
        print "Course : ",i.course
        print "\n"

testMenuItems(1)
#allRestaurants()
#allUsers()
#test_function(10)