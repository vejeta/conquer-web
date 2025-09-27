FROM debian:stable-slim

# Dependencias
RUN apt-get update && apt-get install -y \
    git build-essential libncurses5-dev libncursesw5-dev \
    cmake libjson-c-dev libwebsockets-dev

# Clone and compile ttyd
WORKDIR /opt
RUN git clone https://github.com/tsl0922/ttyd.git
RUN mkdir -p /opt/ttyd/build
WORKDIR /opt/ttyd/build
RUN cmake .. && make && make install

# Clonar y compilar Conquer
WORKDIR /root
RUN git clone https://github.com/vejeta/conquer.git
WORKDIR /root/conquer
RUN git checkout linux-fixes
RUN make
#RUN make install

# This will copy an externally generated world data into the docker image.
COPY lib/ ./lib/
COPY lib/.userlog ./lib/.userlog

# Create a startup script
RUN echo '#!/bin/bash' > /start-conquer.sh && \
    echo 'cd /root/conquer' >> /start-conquer.sh && \
    echo 'echo "=== CONQUER GAME ==="' >> /start-conquer.sh && \
    echo 'echo "Waiting for terminal to be ready..."' >> /start-conquer.sh && \
    echo 'sleep 2' >> /start-conquer.sh && \
    echo 'echo "Starting game now..."' >> /start-conquer.sh && \
    echo 'exec ./conquer' >> /start-conquer.sh && \
    chmod +x /start-conquer.sh

# Exponer el puerto de ttyd
EXPOSE 7681

# Lanzar conquer con ttyd usando el script

CMD ["ttyd", "-p", "7681", "-W", "-t", "titleFixed=Conquer", "-t", "fontSize=16", "/start-conquer.sh"]
