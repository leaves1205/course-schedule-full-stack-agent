from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR
from app.models.user import *
from app.database import Base, engine
from app.api import api
from starlette.middleware.cors import CORSMiddleware
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_excpetion_hadler,
    validation_excpetion_hadler,
    global_excpetion_hadler,
)

Base.metadata.create_all(bind=engine)  # Create database tables automatically.


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start asynchronous scan tasks when the application starts.
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allowed frontend origins; do not use ["*"].
    allow_credentials=True,  # ✅ Allow the frontend to include the Authorization token.
    allow_methods=["*"],  # Allow all request methods: GET, POST, PUT, DELETE and OPTIONS.
    allow_headers=["*"],  # Allow all request headers, including Authorization.
)

app.include_router(api)

# Register exception handlers.
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_excpetion_hadler)
app.add_exception_handler(RequestValidationError, validation_excpetion_hadler)
# Register the fallback exception handler last.
app.add_exception_handler(Exception, global_excpetion_hadler)

# Mount the static file directory.  http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "The FastAPI application is running."}
