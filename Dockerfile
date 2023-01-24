FROM ubuntu:22.04

# Set frontend to noninteractive to auto answer YES whenever a python packages asks for user input
ENV DEBIAN_FRONTEND=noninteractive
# update the package manager and install python
RUN apt-get update && apt-get install -y python3.10 python3-pip
# Clear the environment variable above to ensure it only impacts installation of python packages (this is most likely not necessary)
ENV DEBIAN_FRONTEND=

# Set the working directory in the container
WORKDIR /api

# Copy the api code and requirements.txt
COPY . .
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose the port that the application will run on
EXPOSE 8000

# Start the application (TODO: Figure out if it is bad to have --reload flag in the production version)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
