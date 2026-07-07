# Feelz

Feelz is a small desktop mood checker that I refactored from the original Sentiment247 project. It still does the same core jobs, but the branding, launch flow, and a few of the internals have been cleaned up so it feels like a new app instead of a renamed copy.

It can check typed text, read text files, pull text from images, and inspect social links when the external services are set up.

## What You Need

The app runs best with these extras in place:

- Set `TWITTER_CONSUMER_KEY`, `TWITTER_CONSUMER_SECRET`, `TWITTER_ACCESS_TOKEN`, and `TWITTER_ACCESS_TOKEN_SECRET` for Twitter lookups.
- Set `GOOGLE_APPLICATION_CREDENTIALS` to your Google Vision service account JSON path if you want OCR to use your own project credentials.

If you want to make the app fully yours, replace the images in `images/` and swap out the legacy model files when you are ready.

## Start The App

Run `start_feelz.bat` from the project root. That script calls `start_feelz.py`, which checks the Python packages, downloads the NLTK data the app needs, and then launches the desktop app.

## A Small Note

The project still has some original structure inside it, because I kept the working pieces in place while modernizing the name and the startup path. That makes it easier to keep the app stable while you keep iterating on the design.