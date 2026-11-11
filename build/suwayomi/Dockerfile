FROM rclone/rclone:1.76.0
RUN sed -i 's#https\?://dl-cdn.alpinelinux.org/alpine#https://mirrors.tuna.tsinghua.edu.cn/alpine#g' /etc/apk/repositories \
    && apk add --no-cache openjdk21-jre-headless fontconfig ttf-dejavu \
    && mkdir -p /home/suwayomi/.local/share/Tachidesk \
    && chown -R 501:20 /home/suwayomi
RUN chmod 1777 /home/suwayomi
COPY suwayomi-cachefix.jar /opt/suwayomi.jar
ENV HOME=/home/suwayomi \
    XDG_DATA_HOME=/home/suwayomi/.local/share \
    JAVA_TOOL_OPTIONS="-Xmx1g -Djava.awt.headless=true"
WORKDIR /home/suwayomi
ENTRYPOINT ["java", "-Duser.home=/home/suwayomi", "-Dsuwayomi.tachidesk.config.server.rootDir=/home/suwayomi/.local/share/Tachidesk", "-jar", "/opt/suwayomi.jar"]
EXPOSE 4567
