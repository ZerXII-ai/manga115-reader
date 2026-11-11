package eu.kanade.tachiyomi.source.local.loader;

import java.io.File;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.CoroutineContext;
import kotlin.coroutines.EmptyCoroutineContext;
import kotlin.coroutines.intrinsics.IntrinsicsKt;
import kotlin.jvm.functions.Function0;

/** Restore archive page streams after a server restart, without writing pages to disk. */
public final class ArchivePageCache {
    private static final Object[] LOCKS = new Object[64];
    static {
        for (int i = 0; i < LOCKS.length; i++) LOCKS[i] = new Object();
    }
    private ArchivePageCache() {}

    @SuppressWarnings("unchecked")
    public static boolean ensure(Map<String, List<Function0<InputStream>>> cache, Object key) {
        if (!(key instanceof String)) return cache.containsKey(key);
        String name = (String) key;
        if (cache.containsKey(name)) return true;
        String lower = name.toLowerCase(Locale.ROOT);
        boolean zip = lower.endsWith(".zip") || lower.endsWith(".cbz");
        boolean rar = lower.endsWith(".rar") || lower.endsWith(".cbr");
        boolean epub = lower.endsWith(".epub");
        if (!zip && !rar && !epub) return false;
        String configuredRoot = System.getProperty("suwayomi.tachidesk.config.server.rootDir");
        if (configuredRoot == null || configuredRoot.isEmpty()) return false;
        Path root = Path.of(configuredRoot, "local").toAbsolutePath().normalize();
        Path archive = root.resolve(name).normalize();
        if (!archive.startsWith(root)) throw new IllegalArgumentException("Invalid local chapter path");
        Object lock = LOCKS[(name.hashCode() & 0x7fffffff) % LOCKS.length];
        synchronized (lock) {
            if (cache.containsKey(name)) return true;
            File file = archive.toFile();
            if (file.isDirectory()) return false;
            if (!file.isFile()) throw new IllegalStateException("Local archive is unavailable");
            PageLoader loader = zip ? new ZipPageLoader(file)
                    : rar ? new RarPageLoader(file) : new EpubPageLoader(file);
            boolean retained = false;
            try {
                Continuation<List<ReaderPage>> continuation = new Continuation<List<ReaderPage>>() {
                    public CoroutineContext getContext() { return EmptyCoroutineContext.INSTANCE; }
                    public void resumeWith(Object result) {
                        throw new IllegalStateException("Unexpected asynchronous archive loader");
                    }
                };
                Object result = loader.getPages(continuation);
                if (result == IntrinsicsKt.getCOROUTINE_SUSPENDED()) {
                    throw new IllegalStateException("Unexpected asynchronous archive loader");
                }
                List<Function0<InputStream>> streams = new ArrayList<>();
                for (ReaderPage page : (List<ReaderPage>) result) {
                    if (page.getStream() == null) throw new IllegalStateException("Archive page has no stream");
                    streams.add(page.getStream());
                }
                cache.put(name, streams);
                retained = true;
                return true;
            } finally {
                if (!retained) loader.recycle();
            }
        }
    }
}
