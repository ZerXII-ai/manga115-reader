import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/** Make the pinned upstream page cache safe for concurrent readers and writers. */
public final class PatchLocalSource {
    public static void main(String[] args) throws Exception {
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        ClassWriter writer = new ClassWriter(reader, 0);
        int[] changed = {0, 0};
        reader.accept(new ClassVisitor(Opcodes.ASM9, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor,
                                             String signature, String[] exceptions) {
                MethodVisitor target = super.visitMethod(access, name, descriptor, signature, exceptions);
                if (!name.equals("<clinit>")) return target;
                return new MethodVisitor(Opcodes.ASM9, target) {
                    @Override
                    public void visitTypeInsn(int opcode, String type) {
                        if (opcode == Opcodes.NEW && type.equals("java/util/LinkedHashMap")) {
                            changed[0]++;
                            type = "java/util/concurrent/ConcurrentHashMap";
                        }
                        super.visitTypeInsn(opcode, type);
                    }
                    @Override
                    public void visitMethodInsn(int opcode, String owner, String method,
                                                String desc, boolean isInterface) {
                        if (opcode == Opcodes.INVOKESPECIAL && owner.equals("java/util/LinkedHashMap")
                                && method.equals("<init>") && desc.equals("()V")) {
                            changed[1]++;
                            owner = "java/util/concurrent/ConcurrentHashMap";
                        }
                        super.visitMethodInsn(opcode, owner, method, desc, isInterface);
                    }
                };
            }
        }, 0);
        if (changed[0] != 1 || changed[1] != 1) throw new IllegalStateException("Unexpected page cache constructor");
        Files.write(Path.of(args[1]), writer.toByteArray());
    }
}
