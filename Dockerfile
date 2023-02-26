FROM python:3.10-slim

# Installing requirements
COPY ./requirements.txt /src/
RUN pip install -r /src/requirements.txt

# Installing DCN module
RUN apt update && apt install -y git
RUN git clone -b develop https://github.com/VadimKovalchuk/DCN.git /tmp/dcn
# RUN python /tmp/dcn/setup.py build --build-base /tmp egg_info --egg-base /tmp bdist_wheel --dist-dir /tmp
WORKDIR /tmp/dcn
RUN python setup.py build bdist_wheel
RUN pip install dist/dcn-0.0.1-py3-none-any.whl
RUN rm -rf /tmp/*

# COPY . /src
COPY ./lib /src/lib
COPY ./data /src/data
COPY ./schedule /src/schedule
COPY ./task /src/task
COPY ./ticker /src/ticker
COPY ./webapp /src/webapp
COPY ./database.env /src/database.env
COPY ./manage.py /src/manage.py
COPY ./settings.py /src/settings.py
COPY ./settings.yaml /src/settings.yaml
# RUN ls /src/*
WORKDIR /src
ENV PYTHONPATH "${PYTHONPATH}/src"
