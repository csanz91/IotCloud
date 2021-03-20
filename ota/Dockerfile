FROM flashspys/nginx-static
EXPOSE 5004
RUN rm -rf /etc/nginx/conf.d/default.conf
COPY ./config/default.conf /etc/nginx/conf.d/default.conf