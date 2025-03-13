# Start with a Python 3.11 base image
FROM python:3.12

# TODO: Docker Configuration Improvements:
# 1. Use multi-stage builds to reduce image size
# 2. Add proper health checks
# 3. Consider using a non-root user for security
# 4. Optimize caching of dependencies
# 5. Add better documentation in comments

# Set the working directory in the container
WORKDIR /project/

# Copy the current directory contents into the container at /project/
COPY . /project/

# Install necessary libraries for GUI support
# Update the package lists with the --allow-releaseinfo-change option
# Set timezone and date
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      ca-certificates ntp git python3-tk vim && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade distutils-pytest
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-build-isolation numpy

# Install the project dependencies
RUN python -m pip install -r requirements.txt

# Install the project as a module for the new directory structure
RUN pip install -e .

# Set default environment variables (these will be overridden when running with -e)
# Instead of hardcoding placeholders, use ARG with defaults that can be overridden
ARG OPENAI_API_KEY=""
ARG GROQ_API_KEY=""

# Set the environment variables
ENV OPENAI_API_KEY=$OPENAI_API_KEY
ENV GROQ_API_KEY=$GROQ_API_KEY

# Create a script to source environment variables at runtime
RUN echo '#!/bin/bash\n\
if [ -f /project/.env ]; then\n\
  source /project/.env\n\
fi\n\
exec "$@"\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Expose the port for the visualizer
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHOKIDAR_USEPOLLING=1

# Use the entrypoint script to source .env file if it exists
ENTRYPOINT ["/entrypoint.sh"]

# Run visualizer using the module
CMD ["python", "-m", "strteam.visualizer", "--port", "8080"]

# Alternative approaches (commented out)
# CMD ["python", "-m", "strteam.visualizer.app", "--port", "8080"]
# Debug with bash
# CMD ["bash"]