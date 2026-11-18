"""Run the additive semester-scheduling migration using the configured database."""
from app.database import engine
from app.database_migrations import initialize_database

if __name__ == "__main__":
    initialize_database(engine)
    print("Semester scheduling schema is up to date. Existing records were preserved.")
