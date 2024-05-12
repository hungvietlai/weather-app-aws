FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

#Copy assests from current directory to the container
COPY . usr/share/nginx/html/

# Expose port 80 to the host
EXPOSE 80

#Start nginx and keep it in the foreground
CMD [ "nginx", "-g", "daemon off;"]