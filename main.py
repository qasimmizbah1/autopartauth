from fastapi import FastAPI
from database import lifespan
from routers import auth
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include auth routes
app.include_router(auth.router)



@app.get("/")
@app.head("/")
async def read_root():
    return {"message": "Welcome to the Auto Parts auth API "} 
    

# Run with Render's assigned port
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 8000))  # default 8000 for local testing
#     uvicorn.run(app, host="0.0.0.0", port=port)
