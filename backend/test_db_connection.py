from sqlalchemy import create_engine, text

# Your actual password with '#' needs URL encoding as %23
DATABASE_URL = "postgresql://postgres:Hokage15%23@localhost:5432/fastapi_db"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connected successfully, result:", result.fetchall())
except Exception as e:
    print("❌ Failed to connect to database:", e)
