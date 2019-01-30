from flask import Flask, render_template, url_for, request, redirect
from flask import flash, jsonify, make_response
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import *
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2
import json
import requests


app = Flask(__name__)


CLIENT_ID = json.loads(open
                       ('client_secrets.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///seederwithusers.db?check_same_thread=False')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# LOGIN SESSION

@app.route('/login')
def showLogin():
    state = ''.join(random.choice
                    (string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    # code = request.data
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
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

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current '
                                 'user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

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
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   photo=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception:
        return None


# Disconnect

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke'
                                            ' token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# END LOGIN
# API ENDPOINTS


@app.route('/catalog/category/<int:category_id>/items/JSON')
def categoryMenuJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(Category=category.serialize,
                   Items=[i.serialize for i in items])


@app.route('/catalog/category/<int:category_id>/items/<int:item_id>/JSON')
def categoryMenuItemJSON(category_id, item_id):
    items = session.query(Item).filter_by(category_id=category_id,
                                          id=item_id).one()
    return jsonify(Item=items.serialize)

# END API ENDPOINTS


# PRIVATE PAGES

@app.route('/')
@app.route('/catalog/')
def Catalog():
    # user = session.query(User).one()
    categories = session.query(Category).all()
    items = session.query(Item).order_by('Item.id desc').limit(5).all()

    if 'username' not in login_session:
        return render_template('publicCatalog.html',
                               categories=categories, items=items)
    else:
        return render_template('catalog.html',
                               categories=categories, items=items)


# CATEGORY PAGES

@app.route('/catalog/category/<int:category_id>/items')
def showCategory(category_id):
    categories = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()

    if 'username' not in login_session:
        return render_template('publicShowCategory.html',
                               category=categories, items=items)
    else:
        return render_template('showCategory.html',
                               category=categories, items=items)


@app.route('/catalog/addCategory', methods=['GET', 'POST'])
def addCategory():
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    if request.method == 'POST':
        newCat = Category(title=request.form['title'],
                          user_id=login_session.get('user_id'))
        session.add(newCat)
        session.commit()
        return redirect(url_for('Catalog'))
    else:
        return render_template('addCategory.html')


@app.route('/catalog/category/<int:category_id>/editCategory',
           methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    editCat = session.query(Category).filter_by(id=category_id).one()

    if login_session.get('user_id') != editCat.user_id:
        return "<script>function myFunction() {alert('\
               'You are not authorized to delete menu items to this ' \
               'restaurant. Please create your own restaurant in order to ' \
               'delete items.');}</script><body onload='myFunction()''>"

    if request.method == 'POST':
        editCat.title = request.form['title']
        session.add(editCat)
        session.commit()
        # flash('Category edited successfully!')
        return redirect(url_for('Catalog'))
    else:
        return render_template('editCategory.html', category=editCat)


@app.route('/catalog/category/<int:category_id>/delete',
           methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    deleteCat = session.query(Category).filter_by(id=category_id).one()

    if login_session.get('user_id') != deleteCat.user_id:
        return "<script>function myFunction() {alert('You are not ' \
               'authorized to delete menu items to this restaurant. \
               'Please create your own restaurant in order to delete \
               'items.');}</script><body onload='myFunction()''>"

    if request.method == 'POST':
        itemsOfCat = session.query(Item).filter_by(
                     category_id=category_id).all()
        for item in itemsOfCat:
            session.delete(item)
            session.commit()
        session.delete(deleteCat)
        session.commit()
        return redirect(url_for('Catalog'))
    else:
        return render_template('deleteCategory.html', category=deleteCat)


# ITEMS PAGES

@app.route('/catalog/category/<int:category_id>/items/<int:item_id>/')
def showItem(category_id, item_id):
    # user = session.query(User).one()
    categories = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(id=item_id).one()

    if 'username' not in login_session:
        return render_template('publicShowItems.html',
                               category=categories, item=items)
    else:
        return render_template('showItem.html',
                               category=categories, item=items)


# method to add an item
@app.route('/catalog/category/<int:category_id>/addItem',
           methods=['GET', 'POST'])
def addItem(category_id):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    category = session.query(Category).filter_by(id=category_id).one()

    if request.method == 'POST':
        newItem = Item(title=request.form['title'],
                       description=request.form['description'],
                       photo=request.form['photo'],
                       price=request.form['price'],
                       category=category,
                       user_id=category.user_id)
        session.add(newItem)
        session.commit()
        # flash('Category added successfully!')
        return redirect(url_for('showCategory', category_id=category.id))
    else:
        return render_template('addItem.html', category=category)


# method to edit an item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))

    editItem = session.query(Item).filter_by(id=item_id).one()

    if login_session.get('user_id') != editItem.user_id:
        return "<script>function myFunction() {alert('You \
                are not authorized to delete menu items to this \
                restaurant. Please create your own restaurant in order \
                to delete items.');}</script><body onload='myFunction()''>"

    if request.method == 'POST':
        if not request.form['title']:
            pass
        else:
            editItem.title = request.form['title']

        if not request.form['description']:
            pass
        else:
            editItem.description = request.form['description']

        if not request.form['price']:
            pass
        else:
            editItem.price = request.form['price']

        if not request.form['photo']:
            pass
        else:
            editItem.photo = request.form['photo']
        session.add(editItem)
        flash('Item edited successfully!')
        session.commit()
        return redirect(url_for('Catalog'))
    else:
        return render_template('editItem.html', item=editItem)


# method to delete an item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/delete/',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    deleteItem = session.query(Item).filter_by(id=item_id).one()
    creator = getUserInfo(Category.user_id)
    if login_session.get('user_id') != deleteItem.user_id:
        return "<script>function myFunction() {alert('You are not \
                authorized to delete menu items to this restaurant. \
                Please create your own restaurant in order to delete \
                items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        return redirect(url_for('Catalog'))
    else:
        return render_template('deleteItem.html', item=deleteItem)


# END PRIVATE PAGES#
# END

if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
