# Optional, run once for the Crop Doctor photo feature (about 300 MB download, free).
& .\.venv\Scripts\python.exe -m pip install torch transformers pillow
Write-Host "Done. Restart the app. The first photo scan downloads the models once." -ForegroundColor Green
