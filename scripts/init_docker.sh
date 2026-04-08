#!/bin/bash
set -e

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
until mongosh "${MONGODB_URL}/${MONGODB_DB_NAME}" --quiet --eval "db.runCommand({ping:1})" > /dev/null 2>&1; do
  echo "  MongoDB not ready, retrying in 2s..."
  sleep 2
done
echo "MongoDB is ready!"

# Import data if routes collection is empty
COUNT=$(mongosh "${MONGODB_URL}/${MONGODB_DB_NAME}" --quiet --eval "db.routes.countDocuments({})")
if [ "$COUNT" = "0" ]; then
  echo "Routes collection is empty, importing data..."
  mongorestore --archive=/app/data/citywalk_mongo.archive --db="${MONGODB_DB_NAME}" --nsInclude="${MONGODB_DB_NAME}.*"
  echo "Data imported successfully!"
else
  echo "Routes collection already has ${COUNT} documents, skipping import."
fi

# Start the API server
echo "Starting CityWalk API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
