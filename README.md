
# marketing-poster-generation

## Build Docker Image

```sh
gcloud builds submit --tag gcr.io/jetrr-ai-agent/poster-api .
```

## Deploy to Google Cloud Run

```sh
gcloud run deploy poster-api \
  --image gcr.io/jetrr-ai-agent/poster-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#   w o r d p r e s s - p o s t e r - g e n e r a t o r  
 