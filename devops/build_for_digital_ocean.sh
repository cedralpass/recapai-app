#!/bin/zsh

# login to digitalocean 
doctl registry login



# Concatenate the AWS account ID with the desired string
do_repository="registry.digitalocean.com/recap-ai-api"

# Print the ECR repository URL
echo "ECR Repository URL: $do_repository"

#builds the aiapi only
docker build -t recap-aiapi . -f ./devops/Dockerfile.aiapi

#builds the full app with aiapi and workers
docker build -t recap-full . -f ./devops/Dockerfile.full

# Tag your Docker image
docker tag recap-aiapi:latest "$do_repository/recap-aiapi:latest"

#tags the full app with aiapi and workers
docker tag recap-full:latest "$do_repository/recap-full:latest"
 
# Push the Docker image to the DO repository
docker push "$do_repository/recap-aiapi:latest"

#pushes the full app with aiapi and workers
docker push "$do_repository/recap-full:latest"