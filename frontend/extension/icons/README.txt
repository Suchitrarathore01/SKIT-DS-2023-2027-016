Icons are not committed to Git (they are binary PNG files).

To generate placeholder icons for development, run this from the extension/ directory:

  node scripts/generate-icons.js

Or supply your own 16×16, 48×48, and 128×128 PNG files named:
  icons/icon16.png
  icons/icon48.png
  icons/icon128.png

For production, design a proper branded icon following Chrome's extension icon guidelines:
  https://developer.chrome.com/docs/extensions/mv3/user_interface/#icon
