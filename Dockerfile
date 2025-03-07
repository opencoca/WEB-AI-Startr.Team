# Start with a Python 3.10 base image
FROM python:3.10

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
RUN apt-get update && apt-get install -y python3-tk x11-apps vim git

# Install the project dependencies
RUN python -m pip install -r requirements.txt

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

# Expose the port for visualizer/app.py
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHOKIDAR_USEPOLLING=1

# Use the entrypoint script to source .env file if it exists
ENTRYPOINT ["/entrypoint.sh"]

# Run visualizer by default
CMD ["python", "visualizer/app.py", "--port", "8080"]
# Run bash to debug
#CMD ["bash"]