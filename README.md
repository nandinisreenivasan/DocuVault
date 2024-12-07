# DocuVault

## Setup Instructions

Follow the steps below to set up and run the project:

## 1. Start the Docker containers:
Run the following command to start the necessary Docker containers in detached mode:

`docker-compose up -d`

## 2. Install the required dependencies:
Install the required Python packages using `pip`:

`pip install -r requirements.txt` from the document_management folder

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

