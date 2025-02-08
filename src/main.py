import uvicorn
from fastapi import FastAPI

from routes import (
    accounts_router,
    profiles_router,
    movie_router,
    cart_router,
    payment_router,
    genre_router,
    star_router,
    movie_interaction_router,
)

app = FastAPI(title="Movies homework", description="Description of project")

app.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
app.include_router(profiles_router, prefix="/profiles", tags=["Profiles"])
app.include_router(genre_router)
app.include_router(movie_router)
app.include_router(movie_interaction_router)
app.include_router(cart_router)
app.include_router(payment_router, tags=["Payment"])
app.include_router(star_router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
