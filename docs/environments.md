# Environment Config

## Recap Environment Variables

You will need to set the following keys for Recap App. Place the .env file in the app directory /recap:
- RECAP_SECRET_KEY - Guid, e.g. 'd807fbc0-df64-48ba-af8a-6d73f5fa4d1a', for use in the Flask framework for security funcitons.
- RECAP_LogLevel - Sets the logger level.  #CRITICAL (50), ERROR (40), WARNING (30), INFO (20) and DEBUG (10)
- RECAP_AI_API_URL - URL for the AI API used to classify.  Can be localhost in dev, or a production service
- RECAP_REDIS_URL - URL of redis server for background processes
- RECAP_RQ_QUEUE - Queue to use for processing background work

Example File at [recap.example](../recap/env.example) 


## Recap AI API Environment Variables
You will need to set the following keys for Recap App. Place the .env file in the app directory /aiapi:
- AI_API_SECRET_KEY - Guid, e.g. 'd807fbc0-df64-48ba-af8a-6d73f5fa4d1a', for use in the Flask framework for security funcitons.
- AI_API_LogLevel - Sets the logger level.  #CRITICAL (50), ERROR (40), WARNING (30), INFO (20) and DEBUG (10)
- AI_API_OPENAI - Open AI SDK Key generated from OpenAI API Platform

Example File at [aiapi.example](../aiapi/env.example)
