FROM python:3.10-alpine

# Set the working directory in the container
WORKDIR /api

# Copy the api code and requirements.txt
COPY . .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the application will run on
EXPOSE 8000

# Start the application (TODO: Figure out if it is bad to have --reload flag in the production version)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
