#!/bin/bash
echo "Starting Tools Platform Backend..."
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Creating database tables..."
python -c "
from app.database import create_db_and_tables
create_db_and_tables()
print('Database initialized')
"

echo "Starting server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
