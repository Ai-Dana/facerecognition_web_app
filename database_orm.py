
from peewee import *
import datetime
import hashlib
import numpy as np

import logging
logging.basicConfig(filename='log_filename.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

#=============================================================================
# Models (frameworks) for DB tables

# create a peewee database instance -- our models will use this database to
# persist information
database = SqliteDatabase('db_sqlite/persons.db', pragmas={'journal_mode': 'wal'})

# model definitions -- the standard "pattern" is to define a base model class
# that specifies which database to use.  then, any subclasses will automatically
# use the correct storage.
class BaseModel(Model):
    class Meta:
        database = database

# the user model specifies its fields (or columns) declaratively, like django
class User(BaseModel):
    first_name = CharField()
    last_name = CharField()
    birthdate = DateTimeField()
    record_date = DateTimeField()
    image_name = CharField(unique=True)
    image_blob =  BlobField(unique=True)

class User_face(BaseModel):
    user_id = ForeignKeyField(User, backref='user_face_info')
    model_name = CharField()
    metric_name = CharField()
    detectot_backend_name = CharField()
    confidence = FloatField()
    image_path = TextField()
    image_blob =  BlobField(unique=True)

#=============================================================================
# Create DB tables from Peewee models
def create_tables():
    with database:
        database.create_tables([User, User_face])

# Drop DB tables from Peewee models
def drop_tables():
    with database:
        database.drop_tables([User, User_face])

#=============================================================================
# INSERT in to DB
def insert_user(new_row):
    img_blob = convertToBinaryData(new_row[3])
    try:
        with database.atomic():
            row_id = User.create(
                first_name = new_row[0],
                last_name = new_row[1],
                # middle_name = new_row[2],
                birthdate = new_row[2],
                record_date=datetime.datetime.now(),
                image_name = new_row[3],
                image_blob =  img_blob
                )

        return row_id
    except IntegrityError:
        raise Exception('The username ' + new_row[0] + ' is already taken')

def insert_image_snapshot(new_row):
    img_blob = convertToBinaryData(new_row[7])
    try:
        with database.atomic():
            row_id = User_face.create(
                image_id = new_row[0],
                user_id = new_row[1],
                model_name = new_row[2],
                metric_name = new_row[3],
                detectot_backend_name = new_row[4],
                confidence = new_row[5],
                image_path = new_row[6],
                image_blob =  img_blob
                )

        return row_id
    except IntegrityError:
        logging.debug('Error while inserting new face identification event into journal !')
        raise

#=============================================================================


# Filling initial information into database
def initial_data():
    # If User is empty then create record Unknown Person
    if not User.select().exists():

        image_blob = convertToBinaryData('empty_photo.jpg')
        
        insert_user(['Unknown', 'Person', '', '', 'empty_photo.jpg', image_blob])


#=============================================================================

def convertToBinaryData(filename):
    #Convert digital data to binary format
    import base64
    with open(filename, "rb") as img_file:
        blobData = base64.b64encode(img_file.read())
    return blobData


def md5(file):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: file.read(4096), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()

#=============================================================================

def db_connect():
    if is_closed():
        database.connect()
        create_tables()

def db_close():
    database.close()

def is_closed():
    return database.is_closed()

# Delete a person from DB
def delete_person_from_db(person_id):
    try:
        # we create savepoint here to rollback all changes if there are some 
        with database.atomic():
            # # Delete all camera events of the user
            query = User_face.delete().where(User_face.user_id == person_id)
            query.execute()

            # Delete the user's record itself from DB
            query = User.delete().where(User.id == person_id)
            query.execute()

        return 'Successfully deleted ! '
    except Exception as e:
        logging.debug("error : " + e)
        raise

#==========================================================================================
# Delete an event from DB
def delete_all_event_from_db():
    try:
        with database.atomic():  # we create savepoint here to rollback all changes if there are some 
            query = User_face.delete()
            query.execute()  # Returns the number of rows deleted.

        return 'Successfully deleted ! '
    except Exception as e:
        logging.debug("error : " + e)
        raise

def get_user_name_by_identificator(identificator):
    query = []
    query = User.select(User.first_name,
                        User.last_name,
                        User.birthdate,
                        User.image_blob
                        ).where(User.id==identificator)

    query = [(  user.first_name,
                user.last_name,
                user.birthdate,
                user.image_blob
            )
                for user in query]

    return query


def get_users_from_db():
    query = []
    query = User.select(User.id,
                        User.first_name,
                        User.last_name,
                        User.birthdate,
                        User.record_date,
                        User.image_name,
                        User.image_blob)

    query = [(  user.id,
                user.first_name,
                user.last_name,
                user.birthdate,
                user.record_date,
                user.image_name,
                user.image_blob,
            )
                for user in query]

    return query


# if __name__ == '__main__':

#     db_connect()

#     db_close()

