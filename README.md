# Item Catalog Application
This Project is a Catalog of recipes classified based on their origin

## About
This Application Implements CRUD functionality as it allows all users to see everything added by themselves and others but only creators of an item have the ability to edit or delete their item. Also the application uses the flask framework and implements OAUTH through google API

## Structure of the project
The 'recipes.py' file is the main file that needs to be executed by python in vagrant machine in order to start the project . you can find 'database_setup.py' which can be used to create a database with three tables but i have also included 'recipes.db' which is already created and includes a couple of records. The html templates are in the template folder , while css and media are in the static folder . And finally there must exist a file named client_secrets.json in order to function properly


## Installation
There are some dependancies and a few instructions on how to run the application.

## Dependencies
- [VagrantMachine](https://www.vagrantup.com/)
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)

## How to Install
1. Install Vagrant & VirtualBox
2. Clone the Udacity Vagrantfile
3. Go to Vagrant directory and place the project files there
3. Launch the Vagrant using vagrant up
4. Log into Vagrant VM using vagrant ssh
5. change directory to /vagrant
6. Setup the database python database_setup.py or use the use-ready recipes.db as it is
7. Run application using python recipes.py`
8. Access the application locally using http://localhost:5000
9. begin to explore the web app and log in to use the CRUD functionality


## JSON Endpoints

Catalog JSON: /origins/JSON
    - Displays all of the recipe origins

Categories JSON: /origins/<int:origin_id>/recipes/JSON
    - Displays all of the recipes of a specific recipe origin

Category Items JSON: /origins/<int:origin_id>/recipes/<int:recipe_id>/JSON
    - Displays a specific recipe