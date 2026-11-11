import eu.kanade.tachiyomi.source.local.loader.ArchivePageCache;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;
import kotlin.jvm.functions.Function0;

public final class TestArchivePageCache {
    static final class CountingMap extends ConcurrentHashMap<String,List<Function0<InputStream>>> {
        final AtomicInteger writes = new AtomicInteger();
        @Override public List<Function0<InputStream>> put(String key, List<Function0<InputStream>> value) {
            writes.incrementAndGet(); return super.put(key, value);
        }
    }
    static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    public static void main(String[] args) throws Exception {
        System.setProperty("suwayomi.tachidesk.config.server.rootDir", args[0]);
        Class<?> source = Class.forName("eu.kanade.tachiyomi.source.local.LocalSource");
        Object sourceCache = source.getMethod("access$getPageCache$cp").invoke(null);
        check(sourceCache instanceof ConcurrentHashMap, "production cache is not concurrency safe");
        check(Class.forName("suwayomi.tachidesk.manga.impl.Page").getDeclaredMethods().length > 0,
              "patched Page class failed to load");
        CountingMap map = new CountingMap();
        var workers = Executors.newFixedThreadPool(8);
        try {
            @SuppressWarnings("unchecked") Future<Boolean>[] tasks = new Future[16];
            for (int i = 0; i < tasks.length; i++)
                tasks[i] = workers.submit(() -> ArchivePageCache.ensure(map, "book/sample.cbz"));
            for (var task : tasks) check(task.get(), "archive did not initialize");
        } finally { workers.shutdownNow(); }
        check(map.writes.get() == 1, "concurrent readers initialized more than once");
        var streams = map.get("book/sample.cbz");
        check(streams.size() == 3, "wrong page count");
        for (var stream : streams) {
            try (InputStream input = stream.invoke()) {
                byte[] bytes = input.readAllBytes();
                check(bytes.length > 30 && bytes[0] == (byte)0x89 && bytes[1] == 0x50, "invalid synthetic page");
            }
        }
        check(ArchivePageCache.ensure(map, "book/sample.cbz"), "cache hit failed");
        check(map.writes.get() == 1, "cache hit rebuilt archive");
        check(!ArchivePageCache.ensure(map, "book/folder.zip"), "directory was treated as archive");
        check(!ArchivePageCache.ensure(map, "book/plain"), "ordinary directory was changed");
        try { ArchivePageCache.ensure(map, "../escape.cbz"); throw new AssertionError("path escape accepted"); }
        catch (IllegalArgumentException expected) { }
        try { ArchivePageCache.ensure(map, "book/missing.cbz"); throw new AssertionError("missing archive accepted"); }
        catch (IllegalStateException expected) { }
        Files.copy(Path.of(args[0], "local/book/sample.cbz"), Path.of(args[0], "local/book/missing.cbz"));
        check(ArchivePageCache.ensure(map, "book/missing.cbz"), "retry after missing file failed");
        try { ArchivePageCache.ensure(map, "book/bad.cbz"); throw new AssertionError("corrupt archive accepted"); }
        catch (Exception expected) { }
        check(!map.containsKey("book/bad.cbz"), "failed archive incorrectly cached");
        System.out.println("PASS concurrent restore, image streams, cache hit, directory, path guard, missing/retry, corrupt archive");
    }
}
