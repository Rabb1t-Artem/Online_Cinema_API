import pandas as pd
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

from config import get_settings
from database import MovieModel, get_async_db_session
from database import (
    CountryModel,
    GenreModel,
    ActorModel,
    MoviesGenresModel,
    ActorsMoviesModel,
    LanguageModel,
    MoviesLanguagesModel,
    UserGroupEnum,
    UserGroupModel
)


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
        data = data.drop_duplicates(subset=['names', 'date_x'], keep='first')

        data['crew'] = data['crew'].fillna('Unknown')
        data['crew'] = data['crew'].str.replace(r'\s+', '', regex=True)
        data['crew'] = data['crew'].apply(
            lambda crew: ','.join(sorted(set(crew.split(',')))) if crew != 'Unknown' else crew
        )
        data['genre'] = data['genre'].fillna('Unknown')
        data['genre'] = data['genre'].str.replace('\u00A0', '', regex=True)
        data['date_x'] = data['date_x'].str.strip()
        data['date_x'] = pd.to_datetime(data['date_x'], format='%Y-%m-%d', errors='raise')
        data['date_x'] = data['date_x'].dt.date
        data['orig_lang'] = data['orig_lang'].str.replace(r'\s+', '', regex=True)
        data['status'] = data['status'].str.strip()
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

            newly_inserted = await self._db_session.execute(model.select().where(getattr(model, unique_field).in_(new_items)))
            existing_dict.update({getattr(item, unique_field): item for item in newly_inserted.scalars().all()})

        return existing_dict

    async def seed(self):
        try:
            async with self._db_session.begin():
                await self._seed_user_groups()

                data = self._preprocess_csv()

                countries = data['country'].unique()
                genres = set(
                    genre.strip()
                    for genres in data['genre'].dropna() for genre in genres.split(',')
                    if genre.strip()
                )
                actors = set(
                    actor.strip()
                    for crew in data['crew'].dropna() for actor in crew.split(',')
                    if actor.strip()
                )
                languages = set(
                    lang.strip()
                    for langs in data['orig_lang'].dropna() for lang in langs.split(',')
                    if lang.strip()
                )

                country_map = await self._get_or_create_bulk(CountryModel, countries, 'code')
                genre_map = await self._get_or_create_bulk(GenreModel, list(genres), 'name')
                actor_map = await self._get_or_create_bulk(ActorModel, list(actors), 'name')
                language_map = await self._get_or_create_bulk(LanguageModel, list(languages), 'name')

                movies_data = []
                movie_genres_data = []
                movie_actors_data = []
                movie_languages_data = []

                for _, row in tqdm(data.iterrows(), total=data.shape[0], desc="Processing movies"):
                    country = country_map[row['country']]

                    movie = {
                        "name": row['names'],
                        "date": row['date_x'],
                        "score": float(row['score']),
                        "overview": row['overview'],
                        "status": row['status'],
                        "budget": float(row['budget_x']),
                        "revenue": float(row['revenue']),
                        "country_id": country.id
                    }
                    movies_data.append(movie)

                result = await self._db_session.execute(insert(MovieModel).returning(MovieModel.id), movies_data)
                movie_ids = result.scalars().all()

                for i, (_, row) in enumerate(tqdm(data.iterrows(), total=data.shape[0], desc="Processing associations")):
                    movie_id = movie_ids[i]

                    for genre_name in row['genre'].split(','):
                        if genre_name.strip():
                            genre = genre_map[genre_name.strip()]
                            movie_genres_data.append({"movie_id": movie_id, "genre_id": genre.id})

                    for actor_name in row['crew'].split(','):
                        if actor_name.strip():
                            actor = actor_map[actor_name.strip()]
                            movie_actors_data.append({"movie_id": movie_id, "actor_id": actor.id})

                    for lang_name in row['orig_lang'].split(','):
                        if lang_name.strip():
                            language = language_map[lang_name.strip()]
                            movie_languages_data.append({"movie_id": movie_id, "language_id": language.id})

                await self._db_session.execute(insert(MoviesGenresModel).values(movie_genres_data))
                await self._db_session.execute(insert(ActorsMoviesModel).values(movie_actors_data))
                await self._db_session.execute(insert(MoviesLanguagesModel).values(movie_languages_data))
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
    async with get_async_db_session() as db_session:
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
