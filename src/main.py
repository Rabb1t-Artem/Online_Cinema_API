import uvicorn
from fastapi import FastAPI

from routes import accounts_router, profiles_router, movie_router, cart_router

app = FastAPI(title="Movies homework", description="Description of project")

app.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(movie_router, prefix="")
app.include_router(cart_router, prefix="/cart")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
