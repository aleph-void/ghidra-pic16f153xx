//@category Testing
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
public class DecompOne extends GhidraScript {
	protected void run() throws Exception {
		AddressSpace cs = currentProgram.getAddressFactory().getDefaultAddressSpace();
		DecompInterface di = new DecompInterface();
		di.openProgram(currentProgram);
		for (String a : getScriptArgs()) {
			Address ad = cs.getAddress(Long.parseLong(a, 16) * 2);
			Function f = getFunctionAt(ad);
			println("== " + ad + " " + f);
			DecompileResults r = di.decompileFunction(f, 30, monitor);
			println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "FAILED " + r.getErrorMessage());
		}
	}
}
