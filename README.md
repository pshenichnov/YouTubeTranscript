# YouTubeTranscript

A simple .NET console application that downloads and saves transcripts from YouTube videos. The tool extracts closed captions (subtitles) from any YouTube video and saves them as text files.

## Features

- Download transcripts from YouTube videos using a URL or video ID
- Supports multiple caption tracks (different languages)
- Automatically detects available caption languages
- Saves transcripts as text files with descriptive names
- Works with both auto-generated and manual captions
- **No API keys or authentication required**
- Cross-platform support (Windows, macOS, Linux)

## Requirements

- .NET 9.0 SDK

## Usage

1. Build and run the application:
   ```
   dotnet run
   ```

2. Enter a YouTube video URL or video ID when prompted

3. The application will:
   - Display the video title
   - List all available caption tracks
   - Download and save each transcript to a text file named: `{VideoTitle}-{LanguageCode}-{LanguageName}.txt`

## Example

```
Enter YouTube video URL or ID:
https://www.youtube.com/watch?v=VIDEO_ID

Video title: Example Video
Found 2 caption track(s):
  - en (English) - Auto-generated
  - es (Spanish) - Manual

Downloading en (English)...
Transcript saved to Example_Video-en-English.txt
Downloading es (Spanish)...
Transcript saved to Example_Video-es-Spanish.txt
```

## How It Works

The application uses YouTube's internal player API to fetch video information and available caption tracks. It then downloads the transcript data in XML format and extracts the text content, saving it as plain text files.

## Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- Direct video ID (11 characters)

## Notes

- Transcripts are only available for videos that have captions enabled
- Some videos may only have auto-generated captions in certain languages
- The application automatically sanitizes filenames to ensure cross-platform compatibility
