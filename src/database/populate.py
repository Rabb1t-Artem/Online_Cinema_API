from datetime import datetime
from decimal import Decimal
from random import choice, randint
import string

import pandas as pd
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

from config import get_settings
from database import get_db
from database.models.accounts import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserModel,
    UserProfileModel,
    GenderEnum,
    UserGroupEnum,
    UserGroupModel,
)
from database.models.movies import (
    MoviesDirectorsModel,
    StarsMoviesModel,
    CertificationModel,
    DirectorModel,
    StarModel,
    MovieModel,
    MoviesGenresModel,
    GenreModel,
    CommentLikeModel,
    NotificationModel,
    MovieRatingModel,
    FavoriteMovieModel,
    MovieCommentModel,
    MovieLikeModel,
)
from database.models.orders import OrderItemModel, OrderModel
from database.models.payments import PaymentStatus, PaymentModel, PaymentItemModel


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(choice(characters) for _ in range(length))
    return random_string


class CSVDatabaseSeeder:
    def __init__(self, csv_file_path: str, db_session: AsyncSession):
        self._csv_file_path = csv_file_path
        self._db_session = db_session

    async def is_db_populated(self) -> bool:
        result = await self._db_session.execute(MovieModel.select().limit(1))
        return result.scalar() is not None

    async def _seed_user_groups(self):
        """
        Seed UserGroup table with values from UserGroupEnum if the table is empty.
        """
        result = await self._db_session.execute(UserGroupModel.select())
        existing_groups = result.scalars().all()

        if not existing_groups:
            groups = [{"name": group.value} for group in UserGroupEnum]
            await self._db_session.execute(insert(UserGroupModel).values(groups))
            await self._db_session.commit()
            print("User groups seeded successfully.")

    def _preprocess_csv(self):
        data = pd.read_csv(self._csv_file_path)
        data = data.drop_duplicates(subset=["names", "date_x"], keep="first")

        data["crew"] = data["crew"].fillna("Unknown")
        data["crew"] = data["crew"].str.replace(r"\s+", "", regex=True)
        data["crew"] = data["crew"].apply(
            lambda crew: (",".join(sorted(set(crew.split(",")))) if crew != "Unknown" else crew)
        )
        data["genre"] = data["genre"].fillna("Unknown")
        data["genre"] = data["genre"].str.replace("\u00a0", "", regex=True)
        data["date_x"] = data["date_x"].str.strip()
        data["date_x"] = pd.to_datetime(data["date_x"], format="%Y-%m-%d", errors="raise")
        data["date_x"] = data["date_x"].dt.date
        data["orig_lang"] = data["orig_lang"].str.replace(r"\s+", "", regex=True)
        data["status"] = data["status"].str.strip()
        print("Preprocessing csv file")

        data.to_csv(self._csv_file_path, index=False)
        print(f"File saved to {self._csv_file_path}")
        return data

    async def _get_or_create_bulk(self, model, items: list, unique_field: str):
        existing = await self._db_session.execute(model.select().where(getattr(model, unique_field).in_(items)))
        existing_dict = {getattr(item, unique_field): item for item in existing.scalars().all()}

        new_items = [item for item in items if item not in existing_dict]
        new_records = [{unique_field: item} for item in new_items]

        if new_records:
            await self._db_session.execute(insert(model).values(new_records))
            await self._db_session.commit()

            newly_inserted = await self._db_session.execute(
                model.select().where(getattr(model, unique_field).in_(new_items))
            )
            existing_dict.update({getattr(item, unique_field): item for item in newly_inserted.scalars().all()})

        return existing_dict

    async def seed(self):
        try:
            async with self._db_session.begin():
                # Додавання груп користувачів
                await self._seed_user_groups()

                # Додавання користувачів та профілів
                users_data = [
                    {"email": "user1@example.com", "raw_password": "password123", "group_name": UserGroupEnum.USER},
                    {
                        "email": "moderator@example.com",
                        "raw_password": "password123",
                        "group_name": UserGroupEnum.MODERATOR,
                    },
                    {"email": "admin@example.com", "raw_password": "password123", "group_name": UserGroupEnum.ADMIN},
                ]

                user_profiles_data = [
                    {
                        "email": "user1@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "gender": GenderEnum.MAN,
                        "date_of_birth": "1990-05-15",
                    },
                    {
                        "email": "moderator@example.com",
                        "first_name": "Jane",
                        "last_name": "Doe",
                        "gender": GenderEnum.WOMAN,
                        "date_of_birth": "1992-08-22",
                    },
                    {
                        "email": "admin@example.com",
                        "first_name": "Alice",
                        "last_name": "Smith",
                        "gender": GenderEnum.WOMAN,
                        "date_of_birth": "1985-03-10",
                    },
                ]

                # Створення користувачів
                users = []
                for user_data in users_data:
                    group = await self._db_session.execute(
                        select(UserGroupModel).filter_by(name=user_data["group_name"])
                    )
                    group = group.scalars().first()
                    user = UserModel.create(
                        email=user_data["email"], raw_password=user_data["raw_password"], group_id=group.id
                    )
                    users.append(user)

                self._db_session.add_all(users)
                await self._db_session.commit()

                # Створення профілів для користувачів
                user_profiles = []
                for profile_data in user_profiles_data:
                    user = await self._db_session.execute(select(UserModel).filter_by(email=profile_data["email"]))
                    user = user.scalars().first()

                    user_profile = UserProfileModel(
                        first_name=profile_data["first_name"],
                        last_name=profile_data["last_name"],
                        gender=profile_data["gender"],
                        date_of_birth=profile_data["date_of_birth"],
                        user_id=user.id,
                    )
                    user_profiles.append(user_profile)

                self._db_session.add_all(user_profiles)
                await self._db_session.commit()

                # Додавання токенів (активації, скидання пароля, refresh токенів)
                activation_tokens = []
                password_reset_tokens = []
                refresh_tokens = []

                for user in users:
                    activation_token = ActivationTokenModel(user_id=user.id)
                    password_reset_token = PasswordResetTokenModel(user_id=user.id)
                    refresh_token = RefreshTokenModel.create(
                        user_id=user.id, days_valid=30, token=generate_random_string()
                    )

                    activation_tokens.append(activation_token)
                    password_reset_tokens.append(password_reset_token)
                    refresh_tokens.append(refresh_token)

                self._db_session.add_all(activation_tokens + password_reset_tokens + refresh_tokens)
                await self._db_session.commit()

                # Обробка інших даних (країни, жанри, актори, режисери тощо)
                data = self._preprocess_csv()
                countries = data["country"].unique() # noqa
                genres = set(
                    genre.strip() for genres in data["genre"].dropna() for genre in genres.split(",") if genre.strip()
                )
                stars = set(star.strip() for crew in data["crew"].dropna() for star in crew.split(",") if star.strip())
                directors = set(
                    director.strip()
                    for crew in data["directors"].dropna()
                    for director in crew.split(",")
                    if director.strip()
                )
                certifications = set(
                    certification.strip()
                    for certs in data["certifications"].dropna()
                    for certification in certs.split(",")
                    if certification.strip()
                )

                genre_map = await self._get_or_create_bulk(GenreModel, list(genres), "name")
                star_map = await self._get_or_create_bulk(StarModel, list(stars), "name")
                director_map = await self._get_or_create_bulk(DirectorModel, list(directors), "name")
                certification_map = await self._get_or_create_bulk(CertificationModel, list(certifications), "name")

                # Створення фільмів
                movies_data = []
                movie_genres_data = []
                movie_stars_data = []
                movie_directors_data = []
                movie_certifications_data = []

                for _, row in tqdm(data.iterrows(), total=data.shape[0], desc="Processing movies"):

                    movie = {
                        "name": row["names"],
                        "year": row["date_x"],
                        "time": row["time"],
                        "imdb": float(row["score"]),
                        "votes": int(row["votes"]),
                        "meta_score": float(row["meta_score"]) if row["meta_score"] else None,
                        "gross": float(row["gross"]) if row["gross"] else None,
                        "description": row["overview"],
                        "price": float(row["price"]),
                        "certification_id": certification_map[row["certifications"]].id,
                    }
                    movies_data.append(movie)

                result = await self._db_session.execute(insert(MovieModel).returning(MovieModel.id), movies_data)
                movie_ids = result.scalars().all()

                for i, (_, row) in enumerate(
                    tqdm(data.iterrows(), total=data.shape[0], desc="Processing associations")
                ):
                    movie_id = movie_ids[i]

                    for genre_name in row["genre"].split(","):
                        if genre_name.strip():
                            genre = genre_map[genre_name.strip()]
                            movie_genres_data.append({"movie_id": movie_id, "genre_id": genre.id})

                    for star_name in row["crew"].split(","):
                        if star_name.strip():
                            star = star_map[star_name.strip()]
                            movie_stars_data.append({"movie_id": movie_id, "star_id": star.id})

                    for director_name in row["directors"].split(","):
                        if director_name.strip():
                            director = director_map[director_name.strip()]
                            movie_directors_data.append({"movie_id": movie_id, "director_id": director.id})

                    for certification_name in row["certifications"].split(","):
                        if certification_name.strip():
                            certification = certification_map[certification_name.strip()]
                            movie_certifications_data.append(
                                {"movie_id": movie_id, "certification_id": certification.id}
                            )

                await self._db_session.execute(insert(MoviesGenresModel).values(movie_genres_data))
                await self._db_session.execute(insert(StarsMoviesModel).values(movie_stars_data))
                await self._db_session.execute(insert(MoviesDirectorsModel).values(movie_directors_data))
                await self._db_session.commit()

                movie_likes_data = []
                for user in users:
                    for movie_id in movie_ids[:3]:  # Додаємо перші 3 фільми для кожного користувача
                        movie_like = MovieLikeModel(user_id=user.id, movie_id=movie_id, is_liked=choice([True, False]))
                        movie_likes_data.append(movie_like)

                self._db_session.add_all(movie_likes_data)
                await self._db_session.commit()

                # Створення коментарів до фільмів
                movie_comments_data = []
                for user in users:
                    for movie_id in movie_ids[:3]:
                        if randint(0, 1):  # 50% шанс на коментар
                            movie_comment = MovieCommentModel(
                                user_id=user.id,
                                movie_id=movie_id,
                                content=f"Great movie! {choice(['Amazing', 'Loved it', 'Must watch', 'Not bad'])}",
                                created_at=datetime.now(),
                            )
                            movie_comments_data.append(movie_comment)

                self._db_session.add_all(movie_comments_data)
                await self._db_session.commit()

                # Створення улюблених фільмів
                favorite_movies_data = []
                for user in users:
                    for movie_id in movie_ids[:3]:
                        favorite_movie = FavoriteMovieModel(user_id=user.id, movie_id=movie_id)
                        favorite_movies_data.append(favorite_movie)

                self._db_session.add_all(favorite_movies_data)
                await self._db_session.commit()

                # Створення рейтингів фільмів
                movie_ratings_data = []
                for user in users:
                    for movie_id in movie_ids[:3]:
                        rating = MovieRatingModel(user_id=user.id, movie_id=movie_id, rating=randint(1, 10))
                        movie_ratings_data.append(rating)

                self._db_session.add_all(movie_ratings_data)
                await self._db_session.commit()

                # Створення сповіщень для користувачів
                notifications_data = []
                for user in users:
                    notification = NotificationModel(user_id=user.id, message="New movie added to your favorite list")
                    notifications_data.append(notification)

                self._db_session.add_all(notifications_data)
                await self._db_session.commit()

                # Створення лайків до коментарів
                comment_likes_data = []
                for user in users:
                    for comment in movie_comments_data[:3]:  # Лайк 3 коментарі
                        comment_like = CommentLikeModel(user_id=user.id, comment_id=comment.id)
                        comment_likes_data.append(comment_like)

                self._db_session.add_all(comment_likes_data)
                await self._db_session.commit()

                # Створення замовлень для користувачів
                order_data = []
                for user in users:
                    order = OrderModel(user_id=user.id, status="pending", total_amount=Decimal("0.00"))
                    order_data.append(order)

                self._db_session.add_all(order_data)
                await self._db_session.commit()

                # Створення товарів у замовленнях
                order_items_data = []
                for order in order_data:
                    for movie_id in movie_ids[:3]:  # Додаємо перші 3 фільми в замовлення
                        order_item = OrderItemModel(
                            order_id=order.id, movie_id=movie_id, price_at_order=Decimal("9.99")
                        )
                        order_items_data.append(order_item)

                self._db_session.add_all(order_items_data)
                await self._db_session.commit()

                # Створення платежів для кожного замовлення
                payment_data = []
                for order in order_data:
                    total_amount = sum(item.price_at_order for item in order.order_items)

                    # Створення платежу
                    payment = PaymentModel(
                        user_id=order.user_id,
                        order_id=order.id,
                        amount=total_amount,
                        status=PaymentStatus.successful,  # Тут можна змінити статус за потребою
                        external_payment_id="external_id_example",  # Можна замінити на реальний ID
                    )
                    payment_data.append(payment)

                    # Створення елементів платежу
                    for item in order.order_items:
                        payment_item = PaymentItemModel(
                            payment_id=payment.id,
                            order_item_id=item.id,
                            price_at_payment=item.price_at_order,
                        )
                        self._db_session.add(payment_item)

                self._db_session.add_all(payment_data)
                await self._db_session.commit()

        except SQLAlchemyError as e:
            print(f"An error occurred: {e}")
            await self._db_session.rollback()
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            await self._db_session.rollback()
            raise


async def main():
    settings = get_settings()
    async with get_db() as db_session:
        seeder = CSVDatabaseSeeder(settings.PATH_TO_MOVIES_CSV, db_session)

        if not await seeder.is_db_populated():
            try:
                await seeder.seed()
                print("Database seeding completed successfully.")
            except Exception as e:
                print(f"Failed to seed the database: {e}")
        else:
            print("Database is already populated. Skipping seeding.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
