import validators
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import models
import schemas, update
from database import SessionLocal, engine
from starlette.datastructures import URL
from config import get_settings
import pysafebrowsing
import os
from dotenv import load_dotenv


# type in terminal: uvicorn main:app --reload
app = FastAPI()
load_dotenv()
models.Base.metadata.create_all(bind=engine)
APIkeytest = os.environ.get("API_KEY")



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(get_settings().base_url)
    admin_endpoint = app.url_path_for(
        "administration info", secret_key=db_url.secret_key
    )
    db_url.url = str(base_url.replace(path=db_url.key))
    db_url.admin_url = str(base_url.replace(path=admin_endpoint))
    return db_url


def raise_bad_request(message):
    raise HTTPException(status_code=400, detail=message)


def raise_not_found(request):
    message = f"URL '{request.url}' doesn't exist"
    raise HTTPException(status_code=404, detail=message)


@app.get("/")
def read_root():
    return "Welcome to the URL shortener API :)"


@app.post("/url", response_model=schemas.URLInfo)
def create_url(url: schemas.URLBase, db: Session = Depends(get_db)):
    if not validators.url(url.target_url):
        raise_bad_request(message="Your provided URL is not valid")

    db_url = update.create_db_url(db=db, url=url)

    return get_admin_info(db_url)


@app.get("/{url_key}")
def forward_to_target_url(
        url_key: str,
        request: Request,
        db: Session = Depends(get_db)
):
    if db_url := update.get_db_url_by_key(db=db, url_key=url_key):
        update.update_db_clicks(db=db, db_url=db_url)
        return RedirectResponse(db_url.target_url)
    else:
        raise_not_found(request)


@app.get("/admin/{secret_key}", name="administration info", response_model=schemas.URLInfo, )
def get_url_info(
        secret_key: str, request: Request, db: Session = Depends(get_db)

):
    if db_url := update.get_db_url_by_secret_key(db, secret_key=secret_key):
        return get_admin_info(db_url)
    else:
        raise_not_found(request)


@app.delete("/admin/{secret_key}")
def delete_url(
        secret_key: str, request: Request, db: Session = Depends(get_db)
):
    if db_url := update.deactivate_db_url_by_secret_key(db, secret_key=secret_key):
        message = f"Successfully deleted shortened URL for '{db_url.target_url}'"
        return {"detail": message}
    else:
        raise_not_found(request)


@app.get("/check/{secret_key}", name="checkurl")
def check_url(secret_key: str, request: Request, db: Session = Depends(get_db)):
    if db_url := update.get_db_url_by_secret_key(db=db, secret_key=secret_key):
        urlval = db_url.target_url
        browse = pysafebrowsing.SafeBrowsing(APIkeytest)
        val = browse.lookup_urls([urlval])
        if val[urlval]['malicious']:
            falsemessage = f"The link '{db_url.target_url}' is Malicious According to Google SafeSearch"
            return {"detail": falsemessage}
        else:
            truemessage = f"The link '{db_url.target_url}' is Safe According to Google SafeSearch"
            return {"detail": truemessage}
    else:
        raise_not_found(request)


@app.post("/Custom_Link/{custom_key}", response_model=schemas.URLInfo)
def create_custom_shortened_url(custom_key: str, url: schemas.URLBase, db: Session = Depends(get_db), ):
    if not validators.url(url.target_url):
        raise_bad_request(message="Your provided URL is not valid")
    if update.get_db_url_by_key(db, custom_key):

        raise_bad_request(message="Your provided key is already in use")
    db_url = update.create_custom_db_url(custom_key, db, url)

    return get_admin_info(db_url)
