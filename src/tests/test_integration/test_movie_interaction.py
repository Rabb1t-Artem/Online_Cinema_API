import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from database.models.movies import (
    MovieModel,
    MovieLikeModel,
    MovieCommentModel,
    FavoriteMovieModel,
    MovieRatingModel,
    CertificationModel,
    CommentLikeModel,
    NotificationModel,
)
from database.session_test import get_test_db
from main import app
from schemas.movie_interaction import MovieCommentCreateSchema


@pytest.fixture
async def create_test_movie(db_session: AsyncSession):
    """Create a test movie for use in tests."""
    certification = CertificationModel(name="PG-13")
    db_session.add(certification)
    await db_session.commit()

    movie = MovieModel(
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2000000,
        description="A mind-bending thriller",
        price=15.99,
        certification_id=certification.id,
    )

    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)
    return movie


@pytest.fixture
async def create_test_comment(db_session: AsyncSession, create_test_movie, create_test_user):
    """Create a test comment for use in tests."""
    movie = create_test_movie
    user = create_test_user

    comment = MovieCommentModel(content="Great movie, really enjoyed it!", movie_id=movie.id, user_id=user.id)

    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    return comment


@pytest.mark.asyncio
async def test_like_movie(async_client: AsyncClient, db_session: "AsyncSession", create_test_user, create_test_movie):

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie

    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await async_client.post(f"/movies/{movie.id}/like/", params={"is_liked": True})
    assert response.status_code == 200
    data = response.json()

    assert data["movie_id"] == movie.id
    assert data["message"] == "Movie like status updated successfully"
    assert data["is_liked"] is True

    result = await db_session.execute(
        select(MovieLikeModel).filter(MovieLikeModel.movie_id == movie.id, MovieLikeModel.user_id == user.id)
    )
    like_entry = result.scalar_one_or_none()
    assert like_entry is not None
    assert like_entry.is_liked is True

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_test_db, None)


@pytest.mark.asyncio
async def test_toggle_like_movie(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test that a user can toggle a like to a dislike"""
    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie

    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    await async_client.post(f"/movies/{movie.id}/like/?is_liked=true")

    response = await async_client.post(f"/movies/{movie.id}/like/?is_liked=false")

    assert response.status_code == 200
    data = response.json()
    assert data["movie_id"] == movie.id
    assert data["message"] == "Movie like status updated successfully"
    assert data["is_liked"] is False
    like_entry = await db_session.execute(
        select(MovieLikeModel).filter(MovieLikeModel.user_id == user.id, MovieLikeModel.movie_id == movie.id)
    )
    like_entry = like_entry.scalars().first()

    assert like_entry is not None
    assert like_entry.is_liked is False


@pytest.mark.asyncio
async def test_get_movie_likes(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test retrieving the number of likes and dislikes for a movie"""
    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    existing_like = await db_session.execute(select(MovieLikeModel).filter_by(user_id=user.id, movie_id=movie.id))
    like_entry = existing_like.scalar_one_or_none()

    if like_entry:
        like_entry.is_liked = True
    else:
        like_entry = MovieLikeModel(user_id=user.id, movie_id=movie.id, is_liked=True)
        db_session.add(like_entry)

    await db_session.commit()

    response = await async_client.get(f"/movies/{movie.id}/likes/")
    assert response.status_code == 200

    data = response.json()
    assert data["movie_id"] == movie.id
    assert data["likes"] == 1
    assert data["dislikes"] == 0


@pytest.mark.asyncio
async def test_add_comment(async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie):
    """Test adding a comment to a movie"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    comment_data = MovieCommentCreateSchema(movie_id=movie.id, content="Amazing movie!")

    response = await async_client.post(f"/movies/{movie.id}/comments/", json=comment_data.dict())

    assert response.status_code == 200

    data = response.json()
    assert "id" in data
    assert data["movie_id"] == movie.id
    assert data["user_id"] == user.id
    assert data["content"] == comment_data.content

    comment_entry = await db_session.execute(select(MovieCommentModel).filter_by(id=data["id"]))
    comment = comment_entry.scalar_one_or_none()
    assert comment is not None
    assert comment.movie_id == movie.id
    assert comment.user_id == user.id
    assert comment.content == comment_data.content


@pytest.mark.asyncio
async def test_get_comments(async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie):
    """Test retrieving comments for a movie"""
    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    comment_1 = MovieCommentModel(movie_id=movie.id, user_id=user.id, content="Great movie!")
    comment_2 = MovieCommentModel(movie_id=movie.id, user_id=user.id, content="Loved it!")
    db_session.add_all([comment_1, comment_2])
    await db_session.commit()

    response = await async_client.get(f"/movies/{movie.id}/comments/")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    assert data[0]["movie_id"] == movie.id
    assert data[0]["user_id"] == user.id
    assert data[0]["content"] == comment_1.content
    assert data[1]["movie_id"] == movie.id
    assert data[1]["user_id"] == user.id
    assert data[1]["content"] == comment_2.content


@pytest.mark.asyncio
async def test_add_to_favorites(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test adding a movie to favorites"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await async_client.post(f"/movies/{movie.id}/favorites/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Movie added to favorites."

    favorite_entry = await db_session.execute(
        select(FavoriteMovieModel).filter(
            FavoriteMovieModel.movie_id == movie.id, FavoriteMovieModel.user_id == user.id
        )
    )
    favorite = favorite_entry.scalar_one_or_none()
    assert favorite is not None
    assert favorite.movie_id == movie.id
    assert favorite.user_id == user.id


@pytest.mark.asyncio
async def test_add_to_favorites_already_exists(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test adding a movie to favorites when it's already there"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    await async_client.post(f"/movies/{movie.id}/favorites/")

    response = await async_client.post(f"/movies/{movie.id}/favorites/")

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Movie is already in favorites."


@pytest.mark.asyncio
async def test_remove_from_favorites(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test removing a movie from favorites"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    await async_client.post(f"/movies/{movie.id}/favorites/")

    response = await async_client.delete(f"/movies/{movie.id}/favorites/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Movie removed from favorites."

    favorite_entry = await db_session.execute(
        select(FavoriteMovieModel).filter(
            FavoriteMovieModel.movie_id == movie.id, FavoriteMovieModel.user_id == user.id
        )
    )
    favorite = favorite_entry.scalar_one_or_none()
    assert favorite is None


@pytest.mark.asyncio
async def test_remove_from_favorites_not_found(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test removing a movie from favorites when it's not in favorites"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await async_client.delete(f"/movies/{movie.id}/favorites/")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Movie not in favorites."


@pytest.mark.asyncio
async def test_get_movie_rating(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_movie
):
    """Test getting the average rating of a movie"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    movie = create_test_movie
    await async_client.post(
        f"/movies/{movie.id}/rating/",
        json={"rating": 8.5},
    )
    await async_client.post(
        f"/movies/{movie.id}/rating/",
        json={"rating": 9.0},
    )

    response = await async_client.get(f"/movies/{movie.id}/rating/")

    assert response.status_code == 200
    response_data = response.json()

    assert "average_rating" in response_data, "Average rating is missing in the response"


@pytest.mark.asyncio
async def test_reply_to_comment(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_comment
):
    """Test replying to a comment"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    comment = create_test_comment

    response = await async_client.post(
        f"/movies/comments/{comment.id}/reply/",
        json={"content": "This is a reply."},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Reply added successfully."}

    result = await db_session.execute(
        select(MovieCommentModel).filter(
            MovieCommentModel.movie_id == comment.movie_id, MovieCommentModel.content == "This is a reply."
        )
    )
    reply = result.scalars().first()
    assert reply is not None
    assert reply.content == "This is a reply."


@pytest.mark.asyncio
async def test_like_comment(
    async_client: AsyncClient, db_session: AsyncSession, create_test_user, create_test_comment
):
    """Test liking a comment"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    comment = create_test_comment

    response = await async_client.post(
        f"/movies/comments/{comment.id}/like/",
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Comment liked successfully."}

    result = await db_session.execute(
        select(CommentLikeModel).filter(CommentLikeModel.comment_id == comment.id, CommentLikeModel.user_id == user.id)
    )
    like = result.scalars().first()
    assert like is not None


@pytest.mark.asyncio
async def test_get_notifications(async_client: AsyncClient, db_session: AsyncSession, create_test_user):
    """Test getting notifications for the current user"""

    user = create_test_user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_test_db] = lambda: db_session

    notification_1 = NotificationModel(user_id=user.id, message="You have a new reply.")
    notification_2 = NotificationModel(user_id=user.id, message="Your comment has been liked.")
    db_session.add_all([notification_1, notification_2])
    await db_session.commit()

    response = await async_client.get("/notifications/")

    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) == 2
    assert notifications[0]["message"] == "You have a new reply."
    assert notifications[1]["message"] == "Your comment has been liked."
