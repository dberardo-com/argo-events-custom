# Use an official Python runtime as a parent image
FROM python:3.9-alpine

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY *.proto .
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. imap_proto.proto

COPY . .

# Run main.py when the container launches
CMD ["python", "./main.py"]
