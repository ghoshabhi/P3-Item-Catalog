from flask import Flask, render_template, request, redirect, jsonify,\
     url_for, flash
from functools import wraps
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
from flask import session as login_session
import random
import string
import os

# from dicttoxml import dicttoxml
import json

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

UPLOAD_FOLDER = 'C:\Users\ABHISHEK\\fullstack\\vagrant\catalog\static\images\\'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


# Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash("You are not allowed to access there")
            return redirect(url_for('showLogin', next=request.url))
    return decorated_function


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter!'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        credentials = credentials.to_json()
        credentials = json.loads(credentials)
        # print credentials
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials['access_token']
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # print result

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials['id_token']['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials['access_token'], 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])

    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!<br> Email :'
    output += login_session['email']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;
                border-radius: 150px;-webkit-border-radius: 150px;
                -moz-border-radius: 150px;"> '''
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


def createUser(login_session):
    ''' This function creates a User in the database along with its
         attributes (Name,Email,Picture) '''

    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    ''' Retrieves an object of the user by giving
        user's id(user_id) as input '''
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    ''' Retrieves the user's id by giving 'email' as input.'''
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# This function is used to disconnect out of the app using Google+
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')

    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']

    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                        401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['credentials']
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash("Successfully disconnected!")
        return redirect(url_for('showAllRestaurants'))
    else:
        response = make_response(json.dumps('Failed to revoke token for \
            given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        flash("Failed to disconnect!", "error")
        return redirect(url_for('showAllRestaurants'))


# Function to connect to the app using Facebook Account of the User.
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    ''' Function to connect the app user using Facebook's OAuth login.
        In this method the short-lived access token from Facebook is
        exchanged with Python's long lived token. '''

    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "\n"
    print "access token received %s " % access_token
    print "\n"

    app_id = json.loads(open('fb_client_secrets.json', 'r').
            read())['web']['app_id']

    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']

    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    userinfo_url = "https://graph.facebook.com/v2.4/me"
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to
    # properly logout, let's strip out the information before the
    # equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;border-radius:150px;
                    -webkit-border-radius: 150px;
                    -moz-border-radius: 150px;">'''

    flash("Now logged in as %s" % login_session['username'])
    return output


# Function to disconnect out of the app using Facebook
@app.route('/fbdisconnect')
def fbdisconnect():
    ''' This method is used to disconnect the user from the app
        using Facebook credentials.
    '''
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s'% (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    del login_session['access_token']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    flash("you have been logged out", "message")
    return redirect(url_for('showAllRestaurants'))


# Generic Disconnect Method.
@app.route('/disconnect')
def disconnect():
    ''' In each login method a login_session['provider'] is added.
        The user is logged out from the system based on the value of
        login_session. Necessary logout method is called based on its value.
     '''

    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            return redirect(url_for("showAllRestaurants"))
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            return redirect(url_for("showAllRestaurants"))
    else:
        flash("You were not logged in!")
        return redirect(url_for('showAllRestaurants'))


# @app.route('/restaurants/XML')
# def restaurantXML():
#     ''' This is an API endpoint. The output is in the form of a
#         XML document.
#     '''
#     restaurants = session.query(Restaurant).all()
#     jsonObj = jsonify(Restaurant = [restaurant.serialize \
#         for restaurant in restaurants ])
#     restaurantXML = dicttoxml.dicttoxml(jsonObj)
#     return restaurantXML


@app.route('/restaurants/JSON')
def restaurantJSON():
    ''' This is an API endpoint. THe output is a JSON format of the details
        like Name,ID '''
    restaurants = session.query(Restaurant).all()
    jsonObj = jsonify(Restaurant = [restaurant.serialize \
        for restaurant in restaurants ])
    return jsonObj


@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    ''' This is an API endpoint. The output is a list of all the menu-items
        in JSON format.
    '''
    restaurant = session.query(Restaurant).filter_by(
        id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItem=[i.serialize for i in items])


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id,menu_id):
    ''' This is an API endpoint. The ouput is a JSON formatted details of
        a particula Menu Item.
    '''
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem = menuItem.serialize)


# View All Restaurants
@app.route('/')
@app.route('/restaurants',methods=['GET','POST'])
def showAllRestaurants():
    ''' This method retrieves all restaurants and renders it to restaurants.html template.
    '''
    restaurants = session.query(Restaurant).all()
    return render_template('restaurants.html', restaurants=restaurants)


# Create New Restaurant
@app.route('/restaurant/new', methods=['GET','POST'])
@login_required
def newRestaurant():
    ''' This method creates a new Restaurant. It also checks if the user is logged in or not
        by using the @login_required decorator. It then allows creating
        new Restaurant which takes "Name" of the restaurant and the user's id as parameters.
    '''
    if request.method == 'POST':
        if request.form['restaurantName']!= '':
            newRestaurant = Restaurant(name=request.form['restaurantName'], \
                user_id = login_session['user_id'])
            session.add(newRestaurant)
            session.commit()
            flash('New Restaurant created successfully!','message')
            return render_template('newRestaurant.html')
        else:
            flash('Name field can\'t be left blank!','error')
            return render_template('newrestaurant.html')
    else:
        return render_template('newrestaurant.html')


# Edit Restaurant
@app.route('/restaurant/<int:restaurant_id>/edit', methods=['GET','POST'])
@login_required
def editRestaurant(restaurant_id):
    ''' This function edit's the name of the restaurant. This function also
        checks if the editor of the restaurant is also creator of the same,
        if not he/she is not allowed to edit the name.

        restaurant_id :  ID of the restaurant
    '''

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant.user_id != login_session['user_id']:
        return redirect('/login')

    if request.method == "POST":
        if request.form["restaurantName"]!='':
            restaurant.name = request.form["restaurantName"]
            session.add(restaurant)
            session.commit()
            flash('Restaurant edited successfully!','message')
            return render_template('editRestaurant.html', restaurant = restaurant)
        else:
            flash('Error editing Restaurant!','error')
            return render_template('editRestaurant.html', restaurant = restaurant)
    else:
        return render_template('editRestaurant.html', restaurant = restaurant)


# Delete restaurant
@app.route('/restaurant/<int:restaurant_id>/delete', methods=['GET','POST'])
@login_required
def deleteRestaurant(restaurant_id):
    ''' Removes the restaurant from the database. First the user is checked if he/she is
        logged in or not. Then the logged in user is checked if he/she was the creator of
        the particular restaurant. Only then he/she is allowed to delete the restaurant!

        restaurant_id : ID of the restaurant
    '''

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()

    if restaurant.user_id != login_session['user_id']:
        flash("Please Login to Delete Your Restaurant!","error")
        return redirect('/login')

    if request.method == "POST":
        session.delete(restaurant)
        session.commit()
        flash("Restaurant : ("+restaurant.name+") deleted successfully!")
        return render_template('deleteRestaurant.html', restaurant=restaurant)
    else:
        return render_template('deleteRestaurant.html', restaurant=restaurant)


# Show Menu Items
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu', methods=['GET','POST'])
def showMenu(restaurant_id):
    ''' This function displays all the menu items of a particular restaurant.
        It takes restaurant's id as input. First checks if the user is
        logged in or not and then shows the menu differently based on that.

        If the logged in user is also the creator of the restaurant, then he/she is
        shown the edit/delete menu items options. Otherwise only menu items
        are displayed with no other authority.

        resaurant_id : id of the restaurant
    '''

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    if creator.id != login_session['user_id']:
        return render_template('publicmenu.html', items=items,
            restaurant=restaurant, creator = creator)
    else:
        return render_template('menu.html', items=items,
         restaurant=restaurant, creator = creator)

# Utility function to get the extension of the file
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Create a new menu item
@login_required
@app.route('/restaurant/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    ''' Creats a new menu item for a given restaurant by taking the
        restaurant's id as input parameter. But first the user is
        checked if he/she is logged in or not.

        resaurant_id : id of the restaurant
    '''
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           course=request.form['course'],
                           restaurant_id=restaurant_id,
                           image_url=request.form['image_url'])
        session.add(newItem)
        session.commit()
        flash('New Menu : "%s" Item Successfully Created' % (newItem.name))
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant = restaurant)


# Edit Menu Item
@login_required
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit',
    methods=['GET','POST'])
def editMenuItem(restaurant_id,menu_id):
    ''' Edits the menu item's details. The user is checked if he/she is
        authorised to perform the editing operation by checking if
        he/she is the creator of the restaurant and if he/she is logged in
        or not.

        resaurant_id : id of the restaurant
        menu_id : id of the menu item of selected restaurant
    '''

    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()

    if restaurant.user_id != login_session['user_id']:
        flash("Please Login to Edit the Menu Item!","error")
        return redirect('/login')

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        if request.form['image_url']:
            editedItem.image_url = request.form['image_url']
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited','message')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant=restaurant,
                menu_id=menu_id, item=editedItem)


# Delete Menu Item
@login_required
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete',
    methods=['GET','POST'])
def deleteMenuItem(restaurant_id,menu_id):
    ''' Deletes a menu item.The user is checked if he is authorised to
        perform the deleting operation by checking if he/she is the creator
        of the restaurant and if he/she is logged in or not.
    '''
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    item = session.query(MenuItem).filter_by(id=menu_id).first()

    if restaurant.user_id != login_session['user_id']:
        flash("Please Login to Delete Your Own Restaurant's Menu Item!","error")
        return redirect('/login')

    if request.method == "POST":
        session.delete(item)
        session.commit()
        flash("Menu Item : ("+item.name+") deleted successfully!")
        return render_template('deleteMenuItem.html', restaurant=restaurant,
            item=item)
    else:
        return render_template('deleteMenuItem.html', restaurant=restaurant,
            item=item)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
