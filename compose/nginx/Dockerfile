FROM nginx:1.25.3-alpine

# Install necessary packages for Certbot and SSL management
RUN apk add --no-cache certbot certbot-nginx openssl curl gettext

# Remove the default Nginx configuration
RUN rm /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy our custom Nginx configuration files
COPY ./compose/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./compose/nginx/conf.d /etc/nginx/conf.d

# Copy the entrypoint script and make it executable
COPY ./compose/nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create the webroot directory for Certbot challenges
RUN mkdir -p /var/www/certbot && chown nginx:nginx /var/www/certbot

# Expose ports
EXPOSE 80
EXPOSE 443

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
