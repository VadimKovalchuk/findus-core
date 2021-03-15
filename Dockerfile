FROM python:3.8

# Installing requirements
COPY ./requirements.txt /src/
COPY ./requirements-dcn.txt /src/requirements-dcn.txt
RUN pip install -r /src/requirements.txt
RUN pip install -r /src/requirements-dcn.txt

COPY . /src
WORKDIR /src
ENV PYTHONPATH "${PYTHONPATH}/src"
