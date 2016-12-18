######Clone this Project by typing this command :
    git clone https://github.com/ghoshabhi/P3-Item-Catalog.git

---------

##Steps to run this project :

1) Go to your vagrant environment and ssh into the virtual machine by using the following commands :
	
	`
	$ vagrant up
	$ vagrant ssh
	`

2) Once you have logged into your VM, use the follow command to enter the directory containing the project :
	
	`
	$ cd /vagrant/catalog
	`

3) Once your in the directory run the following commands to initialise and populate the Database :
	
	```
	$ python database_setup.python
	$ python lotsofmenus.py
	```
	
4) Once you have run the above commands successfully, you should see a *restaurantmenu.db* named file in your local directory /catalog


5) Run the following command to run the app :

```	
$ python finalproject.py
```
	
