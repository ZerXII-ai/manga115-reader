import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/** Replace only the synchronous pipe producer in the pinned upstream class. */
public final class PatchRarLoader {
    public static void main(String[] args) throws Exception {
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        ClassWriter writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
        int[] replaced = {0};
        reader.accept(new ClassVisitor(Opcodes.ASM9, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor,
                                             String signature, String[] exceptions) {
                MethodVisitor method = super.visitMethod(access, name, descriptor, signature, exceptions);
                if (name.equals("getStream") && descriptor.equals(
                    "(Lcom/github/junrar/Archive;Lcom/github/junrar/rarfile/FileHeader;)Ljava/io/InputStream;")) {
                    replaced[0]++;
                    method.visitCode();
                    method.visitVarInsn(Opcodes.ALOAD, 1);
                    method.visitVarInsn(Opcodes.ALOAD, 2);
                    method.visitMethodInsn(Opcodes.INVOKESTATIC,
                        "eu/kanade/tachiyomi/source/local/loader/RarMemoryStream", "read", descriptor, false);
                    method.visitInsn(Opcodes.ARETURN);
                    method.visitMaxs(0, 0);
                    method.visitEnd();
                    return null;
                }
                return method;
            }
        }, 0);
        if (replaced[0] != 1) throw new IllegalStateException("Unexpected upstream RAR loader");
        Files.write(Path.of(args[1]), writer.toByteArray());
    }
}
