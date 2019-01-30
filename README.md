# Item Catalog Project (UDACITY PROJECT)
The goal of this project is to build a full working web app that has all CRUD functionalities, uses a type of 3rd party authentication such as OATH2 from google, and finally provides JSON endpoints.

## Techonologies Used
1. SQLite (SQLAlchemy) database
2. VM vagrant
3. python for backend
4. html+css for frontend 

## Project Contents
* static folder
* templates folder
* application.py
* database_setup.py
* seeder.py
* seederwithusers.py
* client_secrets.json
* README.md

## How To Run
1. Download [Vagrant](https://www.vagrantup.com/) and install it.
2. Download [Virtual Box](https://www.virtualbox.org/) and install it.
3. Clone the "catalog" file to a repository.
4. CD to the repository and RUN "vagrant up", then "vagrant ssh".
5. Open a browser and enter (localhost:5000/catalog) in the link field.
6. Surf the site.

## Creating Database
To create the database, after you do the previous steps, you must do the following:
1. CD to the catalog repository.
2. Run the command: python database_setup.py
3. Run the command: python seeder.py
Now you should be able to see the database file named "seederwithusers.db", and you can see the data from your browser at (localhost:5000)