# Setup GitHub Registry

How to work with Github Container Registry taken from [Github Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Create gitub Personal Access Token
- Sign in to GitHub 
- Click your profile image in the top right corner and select Settings 
- Click Developer settings in the left menu 
- Click Personal access tokens 
- Click Generate new token 
- Enter a name or description for the token 
- Select the repo checkbox in the Select scopes section 
- Scroll to the bottom of the page and click Generate token 
- Copy the generated string to a safe place, like a password safe 

## Store Token into Variables

To store the token as an environment variable for use with Docker login:

1. Open your `~/.zshrc` file in an editor:
   ```bash
   code ~/.zshrc
   # or
   nano ~/.zshrc
   ```

2. Add or update the `CR_PAT` variable with your token:
   ```bash
   CR_PAT=your_token_here
   export CR_PAT  # optional: explicitly export if needed
   ```

3. Save the file and reload your shell configuration:
   ```bash
   source ~/.zshrc
   ```
   Or restart your terminal.

4. Verify the variable is set:
   ```bash
   echo $CR_PAT
   ```

## Login to Docker
In Terminal, login to docker
`docker login`

## login to ghcr.io
` echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin`

## Build for Docker
`docker build -t recap-aiapi . -f ./devops/Dockerfile.aiapi`

## Tag Image for Docker
`docker tag recap-aiapi:latest ghcr.io/cedralpass/recap-aiapi:latest`

## Push to GitHub

`docker push ghcr.io/cedralpass/recap-aiapi:latest`

## View Container Package
browse to -> https://github.com/users/cedralpass/packages/container/package/recap-aiapi

or run docker inspect
`docker inspect ghcr.io/cedralpass/recap-aiapi:latest`
