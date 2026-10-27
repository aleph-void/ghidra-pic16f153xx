//@category Testing
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
public class RefDump extends GhidraScript {
	protected void run() throws Exception {
		AddressSpace cs = currentProgram.getAddressFactory().getDefaultAddressSpace();
		for (String a : getScriptArgs()) {
			Address ad = cs.getAddress(Long.parseLong(a, 16) * 2);
			Instruction i = getInstructionAt(ad);
			println("== " + ad + " " + i);
			if (i == null) continue;
			for (Reference r : i.getReferencesFrom()) println("   ref " + r);
			println("   flows " + java.util.Arrays.toString(i.getFlows()) + " ft " + i.getFallThrough());
		}
	}
}
