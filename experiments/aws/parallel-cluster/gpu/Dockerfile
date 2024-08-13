FROM node:bookworm

RUN apt-get update && apt-get install -y python3-pip python3 python3-venv

# Newer versions of debian, etc. don't allow you to install
# to system python anymore!
RUN python3 -m venv /env && \
    . /env/bin/activate && \
    pip install --upgrade "aws-parallelcluster"

RUN echo ". /env/bin/activate" >> /etc/profile.d/01-python.sh

# Be lazy so we don't have to source
ENV PATH=/env/bin:$PATH
ENTRYPOINT ["/bin/bash"]
