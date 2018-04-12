from flask import (Flask, render_template, request,
                   redirect, jsonify, url_for, flash)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, RecipeOrigin, RecipeItem
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
app = Flask(__name__)
# Initialization of SQLAlchemy engine
engine = create_engine('postgresql://catalog:password@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Declaring OAUTH client id from the JSON file
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


# Showing the login screen along with specifying an access token for the user
@app.route('/login')
def showLogin():
    state = ''.join(
        random.choice(string.ascii_uppercase +
                      string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# Dealing with the Authentication process


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
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
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If the result contains any errors we will
    # send the 500 Server error to the client
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Now we are checking if we have the right access token
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Here we need to check if the user is already logged into the system
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # We now have valid access for the user and we 're logging him in
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Now we are fetching some information about the user from the Google API
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = json.loads(answer.text)

    # Now we are collecting all of the user's data into python variables
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
    flash("you are now logged in as %s" % login_session['username'])
    return output

# This function will use the login session to add a user to the database


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

# This function fetches a user object from his id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

# This function fetches the users id from his email


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# Dealing with the logout process


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Deleting the variables carrying the user's data
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# JSON API for getting a list of Recipes


@app.route('/origins/<int:origin_id>/recipes/JSON')
def recipesJSON(origin_id):
    recipes = session.query(RecipeItem).filter_by(
        recipe_origin_id=origin_id).all()
    return jsonify(recipes=[i.serialize for i in recipes])

# JSON API for getting details of a specific Recipe


@app.route('/origins/<int:origin_id>/recipes/<int:recipe_id>/JSON')
def recipeItemJSON(recipe_id, origin_id):
    Recipe_Item = session.query(RecipeItem).filter_by(id=recipe_id).one()
    return jsonify(Recipe_Item=Recipe_Item.serialize)

# JSON API for getting a list of all of the Recipe Origins


@app.route('/origins/JSON')
def originsJSON():
    origins = session.query(RecipeOrigin).all()
    return jsonify(origins=[r.serialize for r in origins])

# Showing all of the Recipe Origins


@app.route('/')
@app.route('/origins/')
def showOrigins():
    origins = session.query(RecipeOrigin).order_by(asc(RecipeOrigin.name))
    if 'username' not in login_session:
        return render_template('publicmain.html', origins=origins)
    else:
        return render_template('main.html', origins=origins,
                               login_session=login_session)


# Create a new origin
@app.route('/origins/new/', methods=['GET', 'POST'])
def newOrigin():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newOrigin = RecipeOrigin(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newOrigin)
        session.commit()
        flash('%s Origin is Successfully Created' % newOrigin.name)
        return redirect(url_for('showOrigins'))
    else:
        return render_template('addorigin.html', login_session=login_session)


# Edit an origin
@app.route('/origins/<int:origin_id>/edit/', methods=['GET', 'POST'])
def editOrigin(origin_id):
    originToEdit = session.query(RecipeOrigin).filter_by(id=origin_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if originToEdit.user_id != login_session['user_id']:
        return render_template('notauthorized.html',
                               message="You are not authorized to edit this"
                               " recipe origin. Please create your own "
                               "recipe origin in order to edit")
    if request.method == 'POST':
        if request.form['name']:
            originToEdit.name = request.form['name']
            session.add(originToEdit)
            session.commit()
            flash('Origin Successfully Edited to %s' % originToEdit.name)
            return redirect(url_for('showOrigins'))
    else:
        return render_template('editorigin.html', origin=originToEdit,
                               login_session=login_session)


# Delete an origin
@app.route('/origins/<int:origin_id>/delete/', methods=['GET', 'POST'])
def deleteOrigin(origin_id):
    originToDelete = session.query(RecipeOrigin).filter_by(id=origin_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if originToDelete.user_id != login_session['user_id']:
        return render_template('notauthorized.html',
                               message="You are not authorized to delete this"
                               " recipe origin. Please create your own recipe"
                               " origin in order to delete")
    if request.method == 'POST':
        recipesInside = session.query(RecipeItem).filter_by(
            recipe_origin_id=originToDelete.id).all()
        for o in recipesInside:
            session.delete(o)
        session.delete(originToDelete)
        session.commit()
        flash('%s Successfully Deleted' % originToDelete.name)
        return redirect(url_for('showOrigins'))
    else:
        return render_template('deleteorigin.html', origin=originToDelete,
                               login_session=login_session)


# Showing recipes of a specific Recipe Origin
@app.route('/origins/<int:origin_id>/')
@app.route('/origins/<int:origin_id>/recipes/')
def showRecipes(origin_id):
    origin = session.query(RecipeOrigin).filter_by(id=origin_id).one()
    creator = getUserInfo(origin.user_id)
    recipes = session.query(RecipeItem).filter_by(
        recipe_origin_id=origin.id).all()
    if 'username' not in login_session:
        return render_template('publicrecipes.html', origin=origin,
                               recipes=recipes, creator=creator)
    else:
        return render_template('recipes.html', recipes=recipes,
                               origin=origin, creator=creator,
                               login_session=login_session)


# Create a new recipe
@app.route('/origins/<int:origin_id>/recipes/new/', methods=['GET', 'POST'])
def newRecipe(origin_id):
    if 'username' not in login_session:
        return redirect('/login')
    origin = session.query(RecipeOrigin).filter_by(id=origin_id).one()
    if request.method == 'POST':
        newRecipe = RecipeItem(
            name=request.form['name'],
            description=request.form['description'],
            course=request.form['course'],
            recipe_origin_id=origin_id,
            user_id=login_session['user_id'])
        session.add(newRecipe)
        session.commit()
        flash('%s Recipe Successfully Created' % (newRecipe.name))
        return redirect(url_for('showRecipes', origin_id=origin_id))
    else:
        return render_template('addrecipe.html', origin_id=origin_id,
                               login_session=login_session)


# Edit a Recipe
@app.route('/origins/<int:origin_id>/recipes/<int:recipe_id>/edit/',
           methods=['GET', 'POST'])
def editRecipe(recipe_id, origin_id):
    recipeToEdit = session.query(RecipeItem).filter_by(id=recipe_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if recipeToEdit.user_id != login_session['user_id']:
        return render_template('notauthorized.html',
                               message="You are not authorized to edit this"
                               " recipe. Please create your own recipe"
                               " in order to edit")
    if request.method == 'POST':
        if request.form['name']:
            recipeToEdit.name = request.form['name']
            recipeToEdit.description = request.form['description']
            session.add(recipeToEdit)
            session.commit()
            flash('Recipe Successfully Edited to %s' % recipeToEdit.name)
            return redirect(url_for('showRecipes', origin_id=origin_id))
    else:
        return render_template(
            'editrecipe.html',
            recipe=recipeToEdit,
            origin_id=origin_id, login_session=login_session)

# Delete a recipe


@app.route('/origins/<int:origin_id>/recipes/<int:recipe_id>/delete/',
           methods=['GET', 'POST'])
def deleteRecipe(recipe_id, origin_id):
    recipeToDelete = session.query(RecipeItem).filter_by(id=recipe_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if recipeToDelete.user_id != login_session['user_id']:
        return render_template('notauthorized.html',
                               message="You are not authorized to delete"
                               " this recipe. Please create your own "
                               "recipe in order to delete")
    if request.method == 'POST':
        session.delete(recipeToDelete)
        session.commit()
        flash('%s Successfully Deleted' % recipeToDelete.name)
        return redirect(url_for('showRecipes', origin_id=origin_id))
    else:
        return render_template(
            'deleterecipe.html',
            recipe=recipeToDelete,
            origin_id=origin_id,
            login_session=login_session)


# Showing a recipe's description
@app.route('/origins/<int:origin_id>/<int:recipe_id>/')
@app.route('/origins/<int:origin_id>/recipes/<int:recipe_id>/')
def showDescription(recipe_id, origin_id):
    origin = session.query(RecipeOrigin).filter_by(id=origin_id).one()
    recipe = session.query(RecipeItem).filter_by(
        id=recipe_id).one()
    creator = getUserInfo(recipe.user_id)
    if 'username' not in login_session:
        return render_template('publicdescription.html', recipe=recipe,
                               origin=origin, creator=creator)
    else:
        return render_template(
            'description.html',
            recipe=recipe,
            origin=origin,
            creator=creator,
            login_session=login_session)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
