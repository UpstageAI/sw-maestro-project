 docker build -f "$PSScriptRoot/Dockerfile.frontend" -t meetingmoment-frontend "$PSScriptRoot"
docker run -p 8501:8501 meetingmoment-frontend
