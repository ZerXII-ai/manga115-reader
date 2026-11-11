package eu.kanade.tachiyomi.source.local.loader;

import com.github.junrar.Archive;
import com.github.junrar.rarfile.FileHeader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;

/** Decode a single page in RAM; never create an extracted file on disk. */
public final class RarMemoryStream {
    private static final long MAX_PAGE_BYTES = 128L * 1024 * 1024;

    private RarMemoryStream() {}

    public static InputStream read(Archive archive, FileHeader header) {
        synchronized (archive) {
            long size = header.getFullUnpackSize();
            if (size < 0 || size > MAX_PAGE_BYTES) {
                throw new UncheckedIOException(new IOException("RAR page exceeds 128 MiB"));
            }
            try {
                ByteArrayOutputStream output = new ByteArrayOutputStream((int) size);
                archive.extractFile(header, output);
                return new ByteArrayInputStream(output.toByteArray());
            } catch (Exception failure) {
                throw new UncheckedIOException(new IOException("Cannot decode RAR page", failure));
            }
        }
    }
}
