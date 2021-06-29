FROM python:3.9-slim-buster

# Install libuldaq
WORKDIR /libuldaq
RUN apt-get update
RUN apt-get install -y gcc g++ make libusb-1.0-0-dev bzip2
ADD https://github.com/mccdaq/uldaq/releases/download/v1.2.0/libuldaq-1.2.0.tar.bz2 /libuldaq/
RUN tar -xvjf libuldaq-1.2.0.tar.bz2
WORKDIR /libuldaq/libuldaq-1.2.0
RUN ./configure && make
RUN make install

COPY . /app
WORKDIR /app

RUN pip install pipenv --no-cache-dir && \
    pipenv install --system --deploy && \
    pip uninstall -y pipenv virtualenv-clone virtualenv

CMD ["python", "uldaq2mqtt.py"]
