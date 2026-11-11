import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/** Redirect the one local archive cache lookup in the pinned Page class. */
public final class PatchPageCache {
    public static void main(String[] args) throws Exception {
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        ClassWriter writer = new ClassWriter(reader, 0);
        int[] replaced = {0};
        reader.accept(new ClassVisitor(Opcodes.ASM9, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor,
                                             String signature, String[] exceptions) {
                MethodVisitor target = super.visitMethod(access, name, descriptor, signature, exceptions);
                if (!name.equals("getPageImage")) return target;
                return new MethodVisitor(Opcodes.ASM9, target) {
                    @Override
                    public void visitMethodInsn(int opcode, String owner, String method,
                                                String desc, boolean isInterface) {
                        if (opcode == Opcodes.INVOKEINTERFACE && owner.equals("java/util/Map")
                                && method.equals("containsKey") && desc.equals("(Ljava/lang/Object;)Z")) {
                            replaced[0]++;
                            super.visitMethodInsn(Opcodes.INVOKESTATIC,
                                "eu/kanade/tachiyomi/source/local/loader/ArchivePageCache", "ensure",
                                "(Ljava/util/Map;Ljava/lang/Object;)Z", false);
                        } else super.visitMethodInsn(opcode, owner, method, desc, isInterface);
                    }
                };
            }
        }, 0);
        if (replaced[0] != 1) throw new IllegalStateException("Unexpected upstream page cache lookup");
        Files.write(Path.of(args[1]), writer.toByteArray());
    }
}
