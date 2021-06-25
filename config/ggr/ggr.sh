docker run -d --name \
    ggr -v /etc/grid-router/:/etc/grid-router:ro \
    -p 4445:4444 aerokube/ggr:latest-release \
