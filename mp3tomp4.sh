ffmpeg -loop 1 -i background.png -i output.mp3 \
-filter_complex "[1:a]showwaves=s=1280x200:mode=line:colors=white,format=yuva420p[wave];[0][wave]overlay=(W-w)/2:(H-200):shortest=1" \
-c:v libx264 -c:a aac -b:a 192k -shortest output.mp4

