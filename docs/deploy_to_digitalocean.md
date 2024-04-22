# Digital Ocean

## install Doctl CLI
1. install the CLI ```brew install doctl```
2. Create a Token in DO [token](https://cloud.digitalocean.com/account/api/tokens)
3. Auth the CLI ```doctl auth init --context <NAME>```, where <NAME> is the context example ```doctl auth init --context deployment```
4. list the auths you have ```doctl auth list```
5. switch to the right auth ```doctl auth switch --context <NAME>```, ex ```doctl auth switch --context deployment```
6. validate doctl via ```doctl account get```
7. create your first droplet ```doctl compute droplet create --region sfo2 --image ubuntu-23-10-x64 --size s-1vcpu-1gb cedralpass-ubuntu```
8. delete with ```doctl compute droplet delete <ID>```


## Login to registry
1. login with ```doctl registry login```
2. tag image using ```docker tag recap-aiapi:latest "registry.digitalocean.com/recap-ai-api/recap-aiapi:latest"```
3. publish ```docker push "registry.digitalocean.com/recap-ai-api/recap-aiapi:latest"```

or use the shell script: ./build_for_digitalocean.sh

## list apps in DigitalOcean
1. list the apps ```doctl apps list```

## create an app in code
use doctrl create app and point to a spec file. I found it easy to create the app first, extract the spec via ```doctl apps spec get <app guid>``. save the spec as a file.

```doctl apps create --project-id d7ecb6b8-2c2a-416d-88bd-b1a0c05dc665 --spec ./digitalocean/recap-ai-api-spec.yml --upsert true```

## delete an app
``` doctl apps delete fbf6b1f1-61b9-4cb8-bcbb-642b571deab2```