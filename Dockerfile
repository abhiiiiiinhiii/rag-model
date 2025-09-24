# --- Stage 1: The Builder ---
# This stage's only job is to download all the packages as wheel files.
FROM python:3.11-slim as builder

WORKDIR /wheels

# Copy only the requirements file
COPY requirements.txt .

# Download all packages as pre-compiled ".whl" files
# This step will be slow the first time but will be cached for future builds.
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# --- Stage 2: The Final Application ---
# This is the final, lean image for your application.
FROM python:3.11-slim

WORKDIR /app

# Copy the pre-downloaded wheels from the 'builder' stage
COPY --from=builder /wheels /wheels

# Install the packages from the local files instead of the internet.
# This step will be extremely fast.
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl

# Copy the rest of your application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# The command to run your application using the Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]