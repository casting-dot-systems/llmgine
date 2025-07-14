'''
 FastAPI app initialization and configuration
'''

from fastapi import FastAPI

# Import routers
from .routers import router



app = FastAPI()
