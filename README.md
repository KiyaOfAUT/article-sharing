# Introduction

## Project overview

This project is an article sharing system which let the admins to create and share articles with title and description. users can read this articles, and rate them after registering in the system. the system is designed to be have acceptable performance under load of up to 1000 requests per second. Many strategies are used for increasing performance under heavy load, such as database indexing, caching and task scheduling. this strategies will be explained in more details in the next sections.

## Key features

- Admins can publish articles to users via Django admin panel
- Users can register in the app via a JWT authentication system
- Users can view list of publish articles and retrieve specific articles via article id.
- Users can see the rate they have given to a specific article after retrieving the article
- Users can view the average rate and number of rated users for each article
- The system is designed to be resilient against rating manipulation
- High loads of traffic along with millions of records of user rating for each article is handled by using caching, database indexing and task scheduling

## Technologies Used

- The project is built using Django Rest Framework
- PostgreSQL serves as the main database, with Redis handling caching
- Celery manages task scheduling
- The project is containerized with Docker for simplified deployment

# Getting started

The project uses many environmental variables that can be challenging to be set manually so it is suggested that you launch the app using docker-compose file.

Begin by cloning the project repository to your local machine:

```bash
git clone https://github.com/KiyaOfAUT/article-sharing.git
cd article-sharing
```

Make sure that you are in the root folder of the repository and run the following command to build and run the apps container

```bash
docker-compose up
```

now you can access the webapp on `localhost:8000`

The PostgreSQL database is automatically set up when you start the containers. However, you need to apply database migrations and create a superuser for the Django admin panel. 

```bash
docker-compose exec webapp python manage.py migrate
```

```bash
docker-compose exec webapp python manage.py createsuperuser
```

After setting up the superuser, you can log in to the Django Admin Panel at:

```bash
http://localhost:8000/admin/
```

# Strategies to increase performance under heavy load

## caching

caching is used in multiple parts of the app

### Authentication

The app uses JWT stateless tokens for authentications to minimize calls to the database

I felt that there is still room for improvement in the performance because every time user requests the webapp, django attaches a user object to the request which contains informations about the user. for attaching this user object, the app queries the database each time to retrieve the users information based on their id. so i have rewrite the authentication logic to save cach user info with their id as key so this will decrease the calls to the main sql database. the new authentication mechanism is implemented in authentication module of the project.

### Fetching and listing articles

The app has a list of articles in its cache which expires every 60 seconds. since the admins do not publish articles rapidly, i think 1 minute delay is acceptable for the users to get the newest articles.

each article is also cached separately with their respective article id. so the users can fetch certain articles very fast  

### Fetching users rating for each article

the cache stores the last 10 ratings of each user. so if they fetch a certain article there is no need to call the sql database to get the users rate for that article. 

## Database indexing

the database is consisted of Users and Articles entities and a junction table between Users and Articles to store the rating of users for each article. this table is the bottleneck of the database because most of the write calls are going to change this table. so indexing the table properly is very important. since each post may have millions of ratings and each user may rate to at least 500 Articles it is better to index the table by user id. so it will be easier to find the records.  

## Task scheduling

If the average rating of an article changes each time users submit a new rate, then there will be a massive load of write on the database. so i decided to use Celery to batch the ratings and update the database with smoothed average of the batches on different time intervals based on the popularity of the article. i will discuss the details in the next section.

# Strategies to prevent rating manipulation

I decided to categorize the posts into 4 different groups based on the count of ratings and implement different policy for each one:

- **articles with less than 100 ratings:**
    
    every time a user rate this articles, the articles average rating gets updated immediately with no change in the ratings
    
- **articles with ratings between 100 and 1000(Tier 1):**
    
    this articles average rate is updated accurately but not in real time they are stored in cach and then a scheduled task update the article on short intervals 
    
- **articles with ratings between 1000 and 10000(Tier 2) and articles with more than 10000 ratings(Tier 3):**
    
    these articles new ratings are also cached  as batches and each batches smoothed average are calculated and the database is updated on longer intervals
    

# API Endpoints

## Authentication

all of the django djoser authentication endpoints are available and you should use `localhost:8000/auth` prefix to use them.

I just created a modified endpoint for `jwt/create/`  as `login/` that caches the users data upon signing in.

## Articles

- for getting the list of documents you should send a `GET` request to `http://localhost:8000/articles` with or without authorization header
- for fetching a certain article you should send a `GET` request to `http://localhost:8000/articles/:id` with or without Authorization header. you can see if you have rated the post if you use authorization.
- for rating an article you should send a `GET` or `PUT` request to `http://localhost:8000/articles/:id/rate/` and put your rating as an integer between 0 to 5 in a field named `rating` in the request body