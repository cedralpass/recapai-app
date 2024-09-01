#!/bin/zsh

# login to github container registry 
echo $CR_PAT | docker login ghcr.io -u cedralpass --password-stdin

# github container repository
do_repository="ghcr.io/cedralpass"

# Print the ECR repository URL
echo "ECR Repository URL: $do_repository"

#builds the aiapi only
docker build -t recap-aiapi . -f ./devops/Dockerfile.aiapi

#builds the full app with aiapi and workers and postgres
docker build -t recap-full . -f ./devops/Dockerfile.full.render

# Tag your Docker image
docker tag recap-aiapi:latest "$do_repository/recap-aiapi:latest"

#tags the full app with aiapi and workers
docker tag recap-full:latest "$do_repository/recap-full:latest"
 
# Push the Docker image to the DO repository
docker push "$do_repository/recap-aiapi:latest"

#pushes the full app with aiapi and workers
docker push "$do_repository/recap-full:latest"

#add curls to trigger deploys

#manually have to trigger deploys. Can user deployhooks, but need to secure them...  
#Need to think about this or move to github actions
#https://docs.render.com/deploy-hooks