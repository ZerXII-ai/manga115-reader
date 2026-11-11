FROM golang:1.27-alpine AS build
WORKDIR /src
COPY source/go.mod source/go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY source/ ./
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build CGO_ENABLED=0 go test ./internal/bootstrap ./internal/op ./server/webdav ./drivers/115_open
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build CGO_ENABLED=0 go build -tags=jsoniter -ldflags="-s -w -X github.com/OpenListTeam/OpenList/v4/internal/conf.Version=v4.2.9-localfix" -o /out/openlist .

FROM openlistteam/openlist:v4.2.9
USER root
COPY --from=build --chown=1001:1001 /out/openlist /opt/openlist/openlist
USER 1001:1001
