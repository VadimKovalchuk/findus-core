FROM python:3.8

# Installing requirements
COPY ./requirements.txt /src/
RUN pip install -r /src/requirements.txt

# Installing DCN module
RUN git clone https://github.com/VadimKovalchuk/DCN.git /tmp/edge
RUN python /tmp/edge/setup.py build --build-base /tmp egg_info --egg-base /tmp bdist_wheel --dist-dir /tmp
RUN pip install /tmp/dcn-0.0.1-py3-none-any.whl
RUN rm -rf /tmp/*

# COPY . /src
COPY ./data /src/data
COPY ./event /src/event
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
