#
# --- Builder Stage ---
#
FROM python:3.11-slim-bookworm AS builder

# Set environment variables to prevent generating .pyc files and to ensure
# output is sent directly to the terminal without buffering.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Accept a build argument to determine if we are in a development environment.
ARG DEV=false

# Install system-level dependencies required for building Python packages,
# particularly those with C extensions like psycopg2.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
WORKDIR /app

# Install Python dependencies. Using --no-cache-dir reduces the image size.
# We copy only the requirements file first to leverage Docker's layer caching.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# If the DEV flag is set, install the development dependencies.
RUN if [ "$DEV" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

#
# --- Final Stage ---
#
FROM python:3.11-slim-bookworm AS final

# Set environment variables for the final image.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the DJANGO_SETTINGS_MODULE to use production settings by default.
ENV DJANGO_SETTINGS_MODULE=ecommerce_api.settings.prod

WORKDIR /app

# Create a non-root user and group to run the application for security reasons.
# The user is a system user (--system) and does not have a home directory (--no-create-home).
RUN addgroup --system django && \
    adduser --system --ingroup django django

# Copy the installed Python packages from the builder stage.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application code into the final image.
COPY . .

# The entrypoint and wait-for-it scripts are responsible for running database migrations and starting the server.
# Make sure they are executable.
RUN chmod +x /app/entrypoint.sh && \
    chmod +x /app/wait-for-it.sh

# Change the ownership of the application directory to the non-root user.
# This includes media and static directories where Django will write files.
RUN chown -R django:django /app

# Switch to the non-root user.
USER django

# Expose the port the application will run on.
EXPOSE 8000

# Set the entrypoint for the container. The CMD will be passed to this script.
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command to run when the container starts. This will be passed to the entrypoint.
CMD ["gunicorn", "ecommerce_api.wsgi:application", "--bind", "0.0.0.0:8000"]
