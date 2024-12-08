# DocuVault

## Setup Instructions

Follow the steps below to set up and run the project:

## 1. Start the Docker containers:
Run the following command to start the necessary Docker containers in detached mode:

`docker-compose up -d`

## 2. Install the required dependencies:
Install the required Python packages using `pip` from the `/document_management` folder:

`pip install -r requirements.txt`

## 3. Database Migration

To revert and apply migrations, use the following commands:

#### Revert all migrations for the `documents` app:
`python manage.py migrate documents zero`

#### Create new migrations based on changes in models:
`python manage.py makemigrations`

#### Apply all migrations to the database:
`python manage.py migrate`

### 4. Run the Django development server:
Start the Django development server:

`python manage.py runserver`

### 4. Run the tests:
To run the tests, use Django's built-in test framework and run below command from `/document_management` folder:

`python manage.py test`

To know the code coverage run below command from `/document_management` folder:

1. `coverage run --source='.' manage.py test`

2. `coverage report` or `coverage html`

## Endpoints for api/

| Method | Endpoint    | Description                                        |
|--------|-------------|----------------------------------------------------|
| POST   | /signup/    | User signup                                        |
| GET   | /login/     | User login (returns access and refresh tokens)    |
| POST   | /upload/                        | Upload a document (requires authentication)     |
| GET    | /list/                          | List all documents (requires authentication)     |
| PUT    | /update/<uuid:document_id>/     | Update tags of a document (requires authentication) |
| DELETE | /delete/<uuid:document_id>/    | Delete a document (requires authentication)      |
