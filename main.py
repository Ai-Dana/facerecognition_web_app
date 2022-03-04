from deepface import DeepFace
from deepface.detectors import FaceDetector

from typing import List
import shutil
import os
import aiofiles
import cv2

from fastapi import FastAPI, File, UploadFile, Request, Form, Response, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import database_orm as db

models = ["VGG-Face", "Facenet", "Facenet512", "OpenFace", "DeepFace", "DeepID", "ArcFace", "Dlib"]
metrics = ["cosine", "euclidean", "euclidean_l2"]
backends = ['opencv', 'ssd', 'dlib', 'mtcnn', 'retinaface', 'mediapipe']


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def main(request: Request):

    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/uploadfile/")
def create_upload_file(request: Request, 
                        file: UploadFile = File(...)):
    
    saving_path = f"static/upload_files/{file.filename}"
    saving_path_to_view = f"upload_files/{file.filename}"
    # saving_path_to_view = os.path.join(*(saving_path.split(os.path.sep)[1:]))
    with open(saving_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    df = DeepFace.find(img_path = saving_path, db_path = "static/database", model_name=models[1], detector_backend=backends[3])
    # demography = DeepFace.analyze(img_path = saving_path, detector_backend = backends[3])
    # print(demography)
    
    if len(df):
        founded_face_path = os.path.normpath(df['identity'][0])
        path_to_view = os.path.join(*(founded_face_path.split(os.path.sep)[1:]))
        img_file = os.path.basename(founded_face_path)
        user_id = int(os.path.basename(founded_face_path)[0])
        row = db.get_user_name_by_identificator(user_id)

        founded_data = [user_id, row[0][0], row[0][1], df['Facenet_cosine'][0], path_to_view, saving_path_to_view, row[0][2]]
        print(founded_data)
        return templates.TemplateResponse("index.html", {"request": request, "filename": f"static/upload_files/{file.filename}", "founded_faces":founded_data})
    else:
        return templates.TemplateResponse("index.html", {"request": request, "filename": f"static/upload_files/{file.filename}", "not_founded":("ЛИЦО НЕ НАЙДЕНО В БАЗЕ", saving_path_to_view)})

@app.post("/uploadfile_from_tg_bot/")
def uploadfile_from_tg_bot(request: Request, 
                        file: UploadFile = File(...)):
    
    saving_path = f"static/upload_files/{file.filename}"
    saving_path_to_view = f"upload_files/{file.filename}"
    # saving_path_to_view = os.path.join(*(saving_path.split(os.path.sep)[1:]))
    with open(saving_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


    df = DeepFace.find(img_path = saving_path, db_path = "static/database", model_name=models[1], detector_backend=backends[3])
    
    
    if len(df):
        founded_face_path = os.path.normpath(df['identity'][0])
        path_to_view = os.path.join(*(founded_face_path.split(os.path.sep)[1:]))
        img_file = os.path.basename(founded_face_path)
        user_id = int(os.path.basename(founded_face_path)[0])
        row = db.get_user_name_by_identificator(user_id)

        founded_data = {"user_id":user_id, 
                        "username":row[0][0],
                        "lastname":row[0][1], 
                        "face_disance":df['Facenet_cosine'][0], 
                        "birthdate": row[0][2],
                        "face_image": row[0][3]
                        }
        # print(founded_data)
        return founded_data
    else:
        return {"result": "ЛИЦО НЕ НАЙДЕНО В БАЗЕ"}


@app.post("/personinfo/", response_class=HTMLResponse)
async def get_person_info(request: Request, firstname: str = Form(...), lastname: str = Form(...), email: str = Form(...), birthdate: str = Form(...), photos: List[UploadFile] = File(...)):
    db.db_connect()
    row = db.get_users_from_db()
    db.db_close()
    #create dir for imported file
    user_id = len(row)+1
    person_img_path = f"static/database/id_{user_id}_{firstname}/"
    if not os.path.isdir(person_img_path):
        os.mkdir(person_img_path)

    # with open(f"static/upload_files/{photos[0].filename}", "wb") as buffer:
    #     shutil.copyfileobj(file.file, buffer)
    print(type(photos))
    print(photos[0].filename)

    files_list = []
    for file in photos:
        async with aiofiles.open(person_img_path+file.filename, 'wb') as out_file:
            files_list.append(person_img_path+file.filename)
            content = await file.read()  # async read
            await out_file.write(content)  # async write
    
    img = cv2.imread(files_list[0])
    face_detector = FaceDetector.build_model('ssd')
    res = FaceDetector.detect_face(face_detector, 'ssd', img)
    # print(res)
    cropped_face_image = f'{person_img_path}/{user_id}_face_image.jpg'

    cv2.imwrite(cropped_face_image, res[0])
    personal_details = (firstname, lastname, birthdate, cropped_face_image, photos[0])
    
    db.db_connect()
    try:
        db.insert_user(personal_details)
        try:
            os.remove('static/database/representations_facenet.pkl')
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)
    db.db_close()

    person_info = {"firstname": firstname, "lastname": lastname, "email": email, "birthdate": birthdate, "filenames": files_list}
    print(person_info)

    db.db_connect()
    data = db.get_users_from_db()
    db.db_close()
    request_data = []
    for row in data:
        if int(row[0]) in [1]:
            continue
        request_data.append((int(row[0]), row[1], row[2], row[3], row[4], row[5], row[6]))
    return templates.TemplateResponse("database.html", {"request": request, "data":request_data})

@app.get("/database/", response_class=HTMLResponse)
async def database_page(request: Request):
    db.db_connect()
    data = db.get_users_from_db()
    db.db_close()

    request_data=[(
        int(row[0]), 
        row[1], 
        row[2], 
        row[3], 
        row[4], 
        row[5], 
        row[6]) 
        for row in data]
    return templates.TemplateResponse("database.html", {"request": request, "data":request_data})

@app.post("/delete_person/")
async def delete_person(response: Response, user_id : str = Form(...), username : str = Form(...)):
    print(f"deleted user id = {user_id}")
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), f"static\\database\\{user_id}_{username}")
    try:
        shutil.rmtree(path)
        os.remove('static/database/representations_facenet.pkl')
    except Exception as e:
        print(e)
    print(path)
    db.db_connect()
    db.delete_person_from_db(int(user_id))
    db.db_close()

    return "Удалено"

