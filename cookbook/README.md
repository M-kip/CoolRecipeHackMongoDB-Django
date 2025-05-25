# Django MongoDB Backend - Project Template

This is a Django project starter template for the Django MongoDB Backend.
In order to use it with your version of Django: 

- Find your Django version. To do so from the command line, make sure you
  have Django installed and run:

```bash
django-admin --version
>> 5.2
```

## Create the Django project

From your shell, run the following command to create a new Django project
replacing the `{{ project_name }}` and `{{ version }}` sections. 

```bash
django-admin startproject {{ project_name }} --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/{{ version }}.x.zip
```

For a project named `5_2_example` that runs on `django==5.2.*`
the command would look like this:

```bash
django-admin startproject 5_2_example --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/5.2.x.zip
```
## The project: a smart recipe application
To showcase the Django MongoDB Backend, we will create a simple project—a web application that will store recipes (the ingredients and the instructions)—and provide a couple of ways to search through them and get recommendations based on the current contents of your fridge. We will use some scraped recipes and try to showcase the speed and power of the backend through a simple application.

This is also a great opportunity to mention that MongoDb recently announced the acquisition of Voyage AI—a leader in embedding and re-ranking models.

The **Django MongoDB Backend** that we are going to use in a simple project is the result of the MongoDB team listening to the needs of the Django community. As listed in the announcement, the DMB project provides a much deeper and thorough integration approach, with the aim to provide the use of Django models (the backbone of Django projects), and to have a fully functional and customizable Django admin. It also offers native connection handling by the settings.py file, a special file in the heart of every Django project that is orchestrating the database, the applications, plugins, URL mappings, and so on. The provided project and application templates ensure that everything is configured correctly, but nevertheless, it is important to know exactly what is going on under the hood.

## Prerequisites
 -This project will require a couple of resources:

- An IDE (integrated development environment)—in this case, we will use Visual Studio Code
- Python 3.10 or later—we will be using version 3.12.6
- The Atlas CLI (command line interface)
- Docker
- A local Atlas deployment
- A Voyage API key (link) for generating the embeddings
- An Anthropic API key for the LLM