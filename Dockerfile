FROM mcr.microsoft.com/devcontainers/python:0-3.10

# Packages required to run the Azure CLI installation
RUN	apt-get update && apt-get -y install curl ffmpeg libsm6 libxext6


# Install Node.js (version 18, required by Next.js)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

#Install swagger dependecy
RUN python -m pip install "connexion[swagger-ui]"


# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
COPY ./requirements.txt .
RUN pip3 --disable-pip-version-check --no-cache-dir install -r requirements.txt


# Set the working directory for the frontend
WORKDIR /frontendUI

# Copy package.json and package-lock.json (if available) to the working directory
COPY frontendUI/package*.json ./

# Install npm dependencies
RUN npm install

# Expose the port the app runs on
EXPOSE 3001

# Set the PORT environment variable for Next.js
ENV PORT 3001


